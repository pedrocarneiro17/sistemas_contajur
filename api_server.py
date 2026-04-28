"""
API standalone para uso externo.
Expõe os sistemas de Extratos e Boletos Pagos como REST API.

Endpoints:
    GET  /api/health
    POST /api/extratos/processar   → retorna JSON com transações
    POST /api/boletos/processar    → retorna JSON com correspondências
"""

import os
import sys
import io
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extrator_contajur.auxiliares.pdf_reader import read_pdf
from extrator_contajur.auxiliares.pdf_reader2 import read_pdf2
from extrator_contajur.banco import get_processor
from extrator_contajur.auxiliares.xml_to_csv import xml_to_csv
from boletos.processador import processar_boletos

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 80 * 1024 * 1024

BANKS_USING_PDF2 = {
    'Asaas', 'Bradesco', 'Sicoob1', 'Sicoob2', 'Sicoob3', 'Stone', 'Sicredi', 'Itaú4',
    'Banco do Brasil1', 'Safra', 'Santander2', 'Efi1', 'Efi2', 'Mercado Pago', 'Caixa2'
}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'OK', 'message': 'API funcionando'})


# ---------------------------------------------------------------------------
# Extratos
# ---------------------------------------------------------------------------


@app.route('/api/extratos/processar', methods=['POST'])
def processar_extratos():
    """
    Recebe um único PDF de extrato bancário e retorna as transações em JSON.

    Form-data:
        file: arquivo PDF

    Resposta de sucesso (200):
        {
            "success": true,
            "banco": str,
            "filename": str,
            "transacoes": [
                {"data": str, "descricao": str, "valor": str, "tipo": str}
            ]
        }
    """
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


# ---------------------------------------------------------------------------
# Boletos Pagos
# ---------------------------------------------------------------------------

@app.route('/api/boletos/processar', methods=['POST'])
def processar_boletos_endpoint():
    """
    Reconcilia boletos pagos entre dois CSVs.

    Form-data:
        csv1: extrato bancário (colunas: data;descrição;valor;tipo)
        csv2: boletos emitidos (skiprows=2, deve conter coluna 'Valor parcela')

    Resposta de sucesso (200):
        {
            "success": true,
            "correspondencias": [{"data": str, "descricao": str, "valor": float}],
            "boletos_sem_correspondencia": [{"data": str, "descricao": str, "valor": float}],
            "total_correspondencias": int,
            "total_sem_correspondencia": int
        }
    """
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


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5501))
    print(f'API server rodando na porta {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
