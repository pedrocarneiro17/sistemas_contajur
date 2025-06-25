from flask import Blueprint, request, send_file, render_template
import pandas as pd
import os
import tempfile
import logging

# Configurar o logging (apenas erros)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Configurar o Blueprint
boletos_bp = Blueprint('boletos', __name__, url_prefix='/boletos')

@boletos_bp.route('/')
def boletos():
    """Rota para renderizar a página de Boletos"""
    return render_template('boletos.html')

@boletos_bp.route('/upload', methods=['POST'])
def upload_files():
    """
    Endpoint para processar dois arquivos CSV e retornar o relatório gerado
    """
    tmp_csv1_path = None
    tmp_csv2_path = None
    tmp_report_path = None

    try:
        if 'csv1' not in request.files or 'csv2' not in request.files:
            return "Erro: Ambos os arquivos CSV (csv1 e csv2) são obrigatórios.", 400

        file1 = request.files['csv1']
        file2 = request.files['csv2']

        if file1.filename == '' or file2.filename == '' or not (file1.filename.endswith('.csv') and file2.filename.endswith('.csv')):
            return "Erro: Apenas arquivos CSV são permitidos.", 400

        # Criar arquivos temporários
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv1_file:
            tmp_csv1_file.write(file1.read())
            tmp_csv1_path = tmp_csv1_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv2_file:
            tmp_csv2_file.write(file2.read())
            tmp_csv2_path = tmp_csv2_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_report_file:
            tmp_report_path = tmp_report_file.name

        # Carregar o primeiro CSV
        df1 = pd.read_csv(tmp_csv1_path, header=None, encoding='latin1', sep=';')
        try:
            # Carregar o segundo CSV, ignorando as duas primeiras linhas e usando a terceira como cabeçalho
            df2 = pd.read_csv(tmp_csv2_path, skiprows=2, encoding='latin1', sep=';', on_bad_lines='skip')
        except pd.errors.ParserError:
            df2 = pd.read_csv(tmp_csv2_path, skiprows=2, encoding='latin1', sep=',', on_bad_lines='skip')

        # Filtrar o primeiro CSV para linhas onde a coluna de status (índice 3) é "D"
        df1_filtered = df1[df1.iloc[:, 3] == 'D']
        df1_filtered['date'] = pd.to_datetime(df1_filtered.iloc[:, 0], format='%d/%m/%Y', errors='coerce')
        df1_filtered['value'] = df1_filtered.iloc[:, 2].apply(lambda x: float(str(x).replace('.', '').replace(',', '.')))

        # Criar um dicionário de tuplas (date, value) para busca eficiente
        matches_dict = dict(zip(df1_filtered['value'], df1_filtered['date']))

        # Localizar a coluna "Valor parcela" no CSV2
        if 'Valor parcela' not in df2.columns:
            return "Erro: A coluna 'Valor parcela' é obrigatória no CSV2.", 400

        # Filtrar o segundo CSV para linhas com valores numéricos na coluna "Valor parcela"
        def is_numeric_value(value):
            try:
                float(str(value).replace('.', '').replace(',', '.'))
                return True
            except ValueError:
                return False

        df2_filtered = df2[df2['Valor parcela'].apply(is_numeric_value)]
        df2_filtered['value'] = df2_filtered['Valor parcela'].apply(lambda x: float(str(x).replace('.', '').replace(',', '.')))

        # Encontrar correspondências
        correspondencias = []
        for index, row in df2_filtered.iterrows():
            value = row['value']
            if value in matches_dict:
                correspondencias.append((matches_dict[value], value))

        # Gerar relatório
        with open(tmp_report_path, 'w', encoding='utf-8') as f:
            f.write("Transações Encontradas nos Dois CSVs (baseado no valor com data do CSV1)\n\n")
            for data, valor in correspondencias:
                f.write(f"Data: {data.strftime('%d/%m/%Y')}, Valor: {valor:.2f}\n")
            f.write(f"\nTotal de correspondências encontradas: {len(correspondencias)}")

        return send_file(
            tmp_report_path,
            as_attachment=True,
            download_name='relatorio_boletos.txt',
            mimetype='text/plain'
        )

    except Exception as e:
        logger.error(f"Erro ao processar os arquivos CSV: {str(e)}")
        return f"Erro ao processar os arquivos: {str(e)}", 400

    finally:
        for path in (tmp_csv1_path, tmp_csv2_path, tmp_report_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    logger.warning(f"Falha ao remover {path}")