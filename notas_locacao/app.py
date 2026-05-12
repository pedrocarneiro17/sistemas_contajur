import io
import re
import concurrent.futures
import pdfplumber
from flask import Blueprint, request, jsonify, send_file, render_template
from flask_cors import CORS

from .processador import processar_nota

notas_locacao_bp = Blueprint('notas_locacao', __name__, url_prefix='/notas-locacao')
CORS(notas_locacao_bp)

_CNPJ_RE = re.compile(r'\d{2}\.?\d{3}\.?\d{3}[/\-]\d{4}[/\-]\d{2}')


def _has_two_cnpjs(text: str) -> bool:
    return len(_CNPJ_RE.findall(text)) >= 2


def _ocr_pdf(file_bytes: bytes) -> str:
    """Fallback OCR via pytesseract (PDFs escaneados)."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(file_bytes, dpi=300)
        print(f"[NOTAS] OCR: {len(images)} página(s) convertida(s)")
        return "\n".join(
            pytesseract.image_to_string(img, lang='por') for img in images
        )
    except Exception as e:
        msg = str(e)
        if 'tesseract is not installed' in msg or 'not in your PATH' in msg:
            print("[NOTAS] OCR indisponível localmente (tesseract não instalado) — usando texto do pdfplumber")
        else:
            print(f"[NOTAS] OCR erro: {e}")
        return ""


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    # 1ª tentativa: pdfplumber
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"[NOTAS] pdfplumber erro: {e}")

    cnpjs = _CNPJ_RE.findall(text)
    print(f"[NOTAS] pdfplumber → {len(text)} chars | CNPJs encontrados: {cnpjs}")

    if _has_two_cnpjs(text):
        print("[NOTAS] texto suficiente via pdfplumber")
        return text

    print("[NOTAS] menos de 2 CNPJs — iniciando OCR...")
    ocr_text = _ocr_pdf(file_bytes)
    ocr_cnpjs = _CNPJ_RE.findall(ocr_text)
    print(f"[NOTAS] OCR → {len(ocr_text)} chars | CNPJs encontrados: {ocr_cnpjs}")

    result = ocr_text if ocr_text.strip() else text
    print(f"[NOTAS] usando {'OCR' if ocr_text.strip() else 'pdfplumber (fallback)'}")
    return result


def _process_single(filename: str, file_bytes: bytes) -> dict:
    print(f"\n[NOTAS] ── processando: {filename} ──")
    try:
        text = _extract_text_from_pdf(file_bytes)
        if not text.strip():
            print(f"[NOTAS] {filename} → nenhum texto extraído")
            return {"filename": filename, "success": False, "error": "Nenhum texto extraído do PDF"}
        result = processar_nota(text)
        result["filename"] = filename
        if result["success"]:
            print(f"[NOTAS] {filename} → ✅ {result['nome_emitente']}")
        else:
            print(f"[NOTAS] {filename} → ❌ {result['error']}")
        return result
    except Exception as e:
        print(f"[NOTAS] {filename} → exceção: {e}")
        return {"filename": filename, "success": False, "linha_f100": None, "nome_emitente": None, "error": str(e)}


@notas_locacao_bp.route('/')
def index():
    return render_template('notas_locacao.html')


@notas_locacao_bp.route('/upload', methods=['POST'])
def upload():
    """
    Recebe múltiplos PDFs de notas de locação e retorna um ZIP com os TXTs F100 gerados.

    Form-data:
        files: um ou mais arquivos PDF

    Resposta de sucesso:
        Content-Type: application/zip
        Body: arquivo ZIP com nota_<nome>_F100.txt para cada PDF processado com sucesso

    Resposta de erro:
        Content-Type: application/json
        {"success": false, "error": "...", "results": [...]}
    """
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado (campo: files)'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

    file_payloads = []
    for file in files:
        if not file or file.filename == '':
            continue
        if not file.filename.lower().endswith('.pdf'):
            file_payloads.append({
                'filename': file.filename,
                'bytes': None,
                'error': 'Extensão inválida (esperado .pdf)',
            })
            continue
        content = file.read()
        if not content.startswith(b'%PDF-'):
            file_payloads.append({
                'filename': file.filename,
                'bytes': None,
                'error': 'Conteúdo não é um PDF válido',
            })
            continue
        file_payloads.append({'filename': file.filename, 'bytes': content, 'error': None})

    results = []

    valid = [p for p in file_payloads if p['bytes'] is not None]
    if valid:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(_process_single, p['filename'], p['bytes'])
                for p in valid
            ]
            for future, p in zip(futures, valid):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({'filename': p['filename'], 'success': False, 'error': str(e)})

    for p in file_payloads:
        if p['error']:
            results.append({'filename': p['filename'], 'success': False, 'error': p['error']})

    successful = [r for r in results if r['success']]

    if not successful:
        sanitized = [{'filename': r['filename'], 'success': r['success'], 'error': r['error']}
                     for r in results]
        return jsonify({
            'success': False,
            'error': 'Nenhum arquivo processado com sucesso',
            'results': sanitized,
        }), 422

    txt_buffer = io.BytesIO(
        '\n'.join(r['linha_f100'] for r in successful).encode('utf-8')
    )
    txt_buffer.seek(0)

    return send_file(
        txt_buffer,
        as_attachment=True,
        download_name='notas.txt',
        mimetype='text/plain',
    )
