import io
from flask import Blueprint, request, jsonify
from flask_cors import CORS

from extrator_contajur.auxiliares.pdf_reader import read_pdf
from extrator_contajur.auxiliares.pdf_reader2 import read_pdf2
from extrator_contajur.banco import get_processor
from extrator_contajur.auxiliares.xml_to_csv import xml_to_csv
from boletos.processador import processar_boletos

api_externa_bp = Blueprint('api_externa', __name__, url_prefix='/api')
CORS(api_externa_bp)

BANKS_USING_PDF2 = {
    'Asaas', 'Bradesco', 'Sicoob1', 'Sicoob2', 'Sicoob3', 'Stone', 'Sicredi', 'Itaú4',
    'Banco do Brasil1', 'Safra', 'Santander2', 'Efi1', 'Efi2', 'Mercado Pago', 'Caixa2'
}


@api_externa_bp.route('/extratos/processar', methods=['POST'])
def processar_extratos():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado (campo: file)'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Extensão inválida (esperado .pdf)'}), 400

    content = file.read()
    if not content.startswith(b'%PDF-'):
        return jsonify({'success': False, 'error': 'Conteúdo não é um PDF válido'}), 400

    file.seek(0)
    try:
        text, bank = read_pdf(file)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao ler PDF: {e}'}), 500

    if bank.startswith('Erro') or bank == 'Banco não identificado':
        return jsonify({'success': False, 'error': 'Banco não identificado'}), 422

    if bank in BANKS_USING_PDF2:
        file.seek(0)
        try:
            text = read_pdf2(file)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Erro ao re-ler PDF: {e}'}), 500

    try:
        processor = get_processor(bank)
        xml_data, _ = processor(text)
        if xml_data is None:
            return jsonify({'success': False, 'error': 'Nenhuma transação encontrada'}), 422
        xml_data.seek(0)
        csv_data = xml_to_csv(xml_data)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro no processamento: {e}'}), 500

    if isinstance(csv_data, io.BytesIO):
        csv_text = csv_data.getvalue().decode('utf-8-sig')
    elif isinstance(csv_data, io.StringIO):
        csv_text = csv_data.getvalue()
    else:
        csv_text = csv_data if isinstance(csv_data, str) else csv_data.decode('utf-8-sig')

    transacoes = []
    for line in csv_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(';')
        if len(parts) >= 4:
            transacoes.append({
                'data': parts[0],
                'descricao': parts[1],
                'valor': parts[2],
                'tipo': parts[3]
            })

    return jsonify({
        'success': True,
        'banco': bank,
        'filename': file.filename,
        'transacoes': transacoes
    })


@api_externa_bp.route('/boletos/processar', methods=['POST'])
def processar_boletos_endpoint():
    if 'csv1' not in request.files or 'csv2' not in request.files:
        return jsonify({'success': False,
                        'error': 'Ambos os arquivos são obrigatórios (csv1 e csv2)'}), 400

    file1 = request.files['csv1']
    file2 = request.files['csv2']

    if file1.filename == '' or file2.filename == '':
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

    try:
        resultado = processar_boletos(file1, file2)
        return jsonify({'success': True, **resultado})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro interno: {e}'}), 500
