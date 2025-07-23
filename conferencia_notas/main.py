from flask import Blueprint, request, jsonify, render_template, send_file
import os
import tempfile
from .utils.pdf_reader import read_pdf_and_identify_model
from .processadores.bling_processor import process_bling_pdf
from .processadores.sgbr_processor import process_sgbr_pdf
from .processadores.fechamento_processor import process_fechamento_pdf
from .utils.excel_processor import remove_duplicatas_e_vazias_xls
import io
import logging

# Configurar o logging (apenas erros)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Configurar o Blueprint
conferencia_bp = Blueprint('conferencia', __name__)

@conferencia_bp.route('/conferencia')
def conferencia():
    """Rota para renderizar a página de conferência"""
    return render_template('conferencia.html')

@conferencia_bp.route('/api/process-pdf', methods=['POST'])
def process_pdf():
    """
    Endpoint para processar um PDF e retornar o Excel gerado
    """
    tmp_pdf_path = None
    tmp_output_pdf_path = None

    try:
        if 'pdf' not in request.files:
            return jsonify({'success': False, 'error': 'Um arquivo PDF é necessário'}), 400

        pdf_file = request.files['pdf']

        if not pdf_file or pdf_file.filename == '':
            return jsonify({'success': False, 'error': 'Arquivo PDF inválido ou não selecionado'}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_file:
            tmp_pdf_file.write(pdf_file.read())
            tmp_pdf_path = tmp_pdf_file.name

        modelo, texto_completo = read_pdf_and_identify_model(tmp_pdf_path)

        if modelo == 'Bling':
            excel_data_from_pdf = process_bling_pdf(texto_completo)
        elif modelo == 'SGBr Sistemas':
            excel_data_from_pdf = process_sgbr_pdf(texto_completo)
        elif modelo == 'Relatório Fechamento Fiscal Entradas':
            excel_data_from_pdf = process_fechamento_pdf(texto_completo)
        else:
            raise ValueError("Modelo de PDF não suportado")

        if isinstance(excel_data_from_pdf, io.BytesIO):
            excel_data_from_pdf = excel_data_from_pdf.getvalue()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_output_pdf_file:
            tmp_output_pdf_file.write(excel_data_from_pdf)
            tmp_output_pdf_path = tmp_output_pdf_file.name

        if not os.path.exists(tmp_output_pdf_path) or os.path.getsize(tmp_output_pdf_path) == 0:
            raise Exception("Falha ao gerar o arquivo Excel a partir do PDF")

        return send_file(
            tmp_output_pdf_path,
            as_attachment=True,
            download_name='pdf_output.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error(f"Erro ao processar o PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao processar o PDF: {str(e)}',
            'results': []
        }), 400

    finally:
        for path in (tmp_pdf_path, tmp_output_pdf_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    logger.warning(f"Falha ao remover {path}")

@conferencia_bp.route('/api/process-excel', methods=['POST'])
def process_excel():
    """
    Endpoint para processar um Excel enviado e retornar o Excel processado
    """
    tmp_excel_path = None
    tmp_output_excel_path = None

    try:
        if 'excel' not in request.files:
            return jsonify({'success': False, 'error': 'Um arquivo Excel é necessário'}), 400

        excel_file = request.files['excel']

        if not excel_file or excel_file.filename == '':
            return jsonify({'success': False, 'error': 'Arquivo Excel inválido ou não selecionado'}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp_excel_file:
            tmp_excel_file.write(excel_file.read())
            tmp_excel_path = tmp_excel_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_output_excel_file:
            tmp_output_excel_file.write(b'')  # Inicializa o arquivo
            tmp_output_excel_path = tmp_output_excel_file.name
            remove_duplicatas_e_vazias_xls(tmp_excel_path, tmp_output_excel_path)

        if not os.path.exists(tmp_output_excel_path) or os.path.getsize(tmp_output_excel_path) == 0:
            raise Exception("Falha ao gerar o arquivo Excel processado")

        return send_file(
            tmp_output_excel_path,
            as_attachment=True,
            download_name='excel_output.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error(f"Erro ao processar o Excel: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao processar o Excel: {str(e)}',
            'results': []
        }), 400

    finally:
        for path in (tmp_excel_path, tmp_output_excel_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    logger.warning(f"Falha ao remover {path}")