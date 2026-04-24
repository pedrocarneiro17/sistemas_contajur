import io
import zipfile
import concurrent.futures
import pdfplumber
from flask import Blueprint, request, jsonify, send_file, render_template
from flask_cors import CORS

from .processador import processar_nota

notas_locacao_bp = Blueprint('notas_locacao', __name__, url_prefix='/notas-locacao')
CORS(notas_locacao_bp)


def _extract_text_from_pdf(file) -> str:
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def _process_single(filename: str, file_bytes: bytes) -> dict:
    try:
        text = _extract_text_from_pdf(io.BytesIO(file_bytes))
        if not text.strip():
            return {"filename": filename, "success": False, "error": "Nenhum texto extraído do PDF"}
        result = processar_nota(text)
        result["filename"] = filename
        return result
    except Exception as e:
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
            futures = {
                executor.submit(_process_single, p['filename'], p['bytes']): p
                for p in valid
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    info = futures[future]
                    results.append({'filename': info['filename'], 'success': False, 'error': str(e)})

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

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for r in successful:
            txt_name = f"{r['filename'].rsplit('.', 1)[0]}.txt"
            zf.writestr(txt_name, r['linha_f100'] + '\n')
    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name='notas.zip',
        mimetype='application/zip',
    )
