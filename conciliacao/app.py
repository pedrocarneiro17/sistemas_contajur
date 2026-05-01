import io
import zipfile
from flask import Blueprint, request, send_file, render_template, jsonify
from flask_cors import CORS
from .processador import processar

conciliacao_bp = Blueprint('conciliacao', __name__, url_prefix='/conciliacao')
CORS(conciliacao_bp)


@conciliacao_bp.route('/')
def index():
    return render_template('conciliacao.html')


@conciliacao_bp.route('/processar', methods=['POST'])
def processar_endpoint():
    if 'extrato' not in request.files or 'base' not in request.files:
        return jsonify({'success': False, 'error': 'Envie os dois arquivos (extrato e base)'}), 400

    extrato_file = request.files['extrato']
    base_file    = request.files['base']

    if not extrato_file.filename or not base_file.filename:
        return jsonify({'success': False, 'error': 'Arquivos não selecionados'}), 400

    try:
        excel_buf, csv_buf = processar(extrato_file.read(), base_file.read())

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('analise_conciliacao.xlsx', excel_buf.getvalue())
            zf.writestr('extrato_pendente.csv',     csv_buf.getvalue())
        zip_buf.seek(0)

        nome = extrato_file.filename.rsplit('.', 1)[0]
        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=f'conciliacao_{nome}.zip',
            mimetype='application/zip',
        )

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro interno: {e}'}), 500
