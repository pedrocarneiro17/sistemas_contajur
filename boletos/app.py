from flask import Blueprint, request, send_file, render_template
import pandas as pd
import os
import tempfile
import logging
import re # Importado para usar expressões regulares

# Configurar o logging (apenas erros)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Configurar o Blueprint
boletos_bp = Blueprint('boletos', __name__, url_prefix='/boletos')

# --- FUNÇÃO AUXILIAR PARA LIMPEZA DE NÚMEROS ---
def clean_and_convert_to_float(value):
    """
    Limpa uma string removendo caracteres não numéricos (exceto vírgula)
    e a converte para float. Lida com formatos como 'R$ 1.234,56'.
    """
    try:
        # Garante que o valor é uma string
        s_value = str(value)
        # Remove caracteres que não são dígitos ou vírgula (ex: 'R$', espaços)
        # Nota: Mantemos o ponto para casos onde o formato já é '1234.56'
        cleaned_s = re.sub(r'[^\d,.]', '', s_value).strip()
        
        # Lida com o formato brasileiro (ex: 1.234,56)
        if ',' in cleaned_s and '.' in cleaned_s:
            # Remove o ponto de milhar
            cleaned_s = cleaned_s.replace('.', '')
        
        # Troca a vírgula decimal por ponto
        cleaned_s = cleaned_s.replace(',', '.')
        
        return float(cleaned_s)
    except (ValueError, TypeError):
        # Se mesmo após a limpeza não for um número válido, retorna 0.0 ou lança erro
        # Retornar 0.0 pode ser mais seguro para evitar que a aplicação quebre
        return 0.0


@boletos_bp.route('/')
def boletos():
    """Rota para renderizar a página de Boletos"""
    return render_template('boletos.html')

@boletos_bp.route('/upload', methods=['POST'])
def upload_files():
    """
    Endpoint para processar dois arquivos CSV e retornar o relatório gerado.
    Inclui: 1) Correspondências entre CSVs baseado no valor com data e descrição do CSV1.
            2) Boletos sem correspondência no CSV1 com palavras-chave específicas.
    """
    tmp_csv1_path = None
    tmp_csv2_path = None
    tmp_report_path = None

    try:
        if 'csv1' not in request.files or 'csv2' not in request.files:
            return "Erro: Ambos os arquivos CSV (csv1 e csv2) são obrigatórios.", 400

        file1 = request.files['csv1']
        file2 = request.files['csv2']

        if file1.filename == '' or file2.filename == '':
            return "Erro: Nenhum arquivo selecionado.", 400
        
        # A validação de .csv é útil, mas o código robusto abaixo é a proteção real
        if not (file1.filename.endswith('.csv') and file2.filename.endswith('.csv')):
            logger.warning(f"Aviso: Um dos arquivos enviados não tem a extensão .csv. Nome do arquivo 1: {file1.filename}, Nome do arquivo 2: {file2.filename}")
            # Você pode optar por retornar um erro aqui ou tentar processar mesmo assim
            # return "Erro: Apenas arquivos com a extensão .csv são permitidos.", 400

        # Criar arquivos temporários
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv1_file:
            # Ler como bytes e decodificar para utf-8, ignorando erros de decodificação
            file_content = file1.read()
            try:
                tmp_csv1_file.write(file_content.decode('utf-8').encode('utf-8'))
            except UnicodeDecodeError:
                tmp_csv1_file.write(file_content.decode('latin1').encode('utf-8'))
            tmp_csv1_path = tmp_csv1_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv2_file:
            file_content = file2.read()
            try:
                tmp_csv2_file.write(file_content.decode('utf-8').encode('utf-8'))
            except UnicodeDecodeError:
                tmp_csv2_file.write(file_content.decode('latin1').encode('utf-8'))
            tmp_csv2_path = tmp_csv2_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_report_file:
            tmp_report_path = tmp_report_file.name

        # Carregar o primeiro CSV
        df1 = pd.read_csv(tmp_csv1_path, header=None, encoding='utf-8', sep=';', on_bad_lines='warn')
        try:
            # Carregar o segundo CSV, ignorando as duas primeiras linhas e usando a terceira como cabeçalho
            df2 = pd.read_csv(tmp_csv2_path, skiprows=2, encoding='utf-8', sep=';', on_bad_lines='skip')
        except pd.errors.ParserError:
            df2 = pd.read_csv(tmp_csv2_path, skiprows=2, encoding='utf-8', sep=',', on_bad_lines='skip')
        except Exception:
            # Tenta com latin1 como último recurso
            df2 = pd.read_csv(tmp_csv2_path, skiprows=2, encoding='latin1', sep=';', on_bad_lines='skip')


        # Filtrar o primeiro CSV para linhas onde a coluna de status (índice 3) é "D"
        df1_filtered = df1[df1.iloc[:, 3] == 'D'].copy() # Usar .copy() para evitar SettingWithCopyWarning
        df1_filtered['date'] = pd.to_datetime(df1_filtered.iloc[:, 0], format='%d/%m/%Y', errors='coerce')
        # Aplicar a função de limpeza robusta
        df1_filtered['value'] = df1_filtered.iloc[:, 2].apply(clean_and_convert_to_float)

        # Criar um dicionário de tuplas (date, description, value) para busca eficiente
        matches_dict = dict(zip(df1_filtered['value'], zip(df1_filtered['date'], df1_filtered.iloc[:, 1])))

        # Localizar a coluna "Valor parcela" no CSV2
        if 'Valor parcela' not in df2.columns:
            return "Erro: A coluna 'Valor parcela' é obrigatória no CSV2.", 400

        # Função de verificação atualizada
        def is_numeric_value(value):
            try:
                clean_and_convert_to_float(value)
                return True
            except (ValueError, TypeError):
                return False

        df2_filtered = df2[df2['Valor parcela'].apply(is_numeric_value)].copy()
        # Aplicar a função de limpeza robusta
        df2_filtered['value'] = df2_filtered['Valor parcela'].apply(clean_and_convert_to_float)

        # Encontrar correspondências
        correspondencias = []
        for index, row in df2_filtered.iterrows():
            value = row['value']
            if value in matches_dict:
                date, description = matches_dict[value]
                correspondencias.append((date, description, value))

        # Filtrar transações do CSV1 com palavras-chave na descrição (coluna 1)
        palavras_chave = ['DÉB. TIT. COBRANÇA', 'DÉB.TIT.COB.EFETIV', 'DÉB.TIT.COMPE.EFETI', 'SIPAG FORNECEDORES', 'PAGTO ELETRON', 'boleto', 'Boleto', 'BOLETO', 'DÉB.PGTO.BOLETO INT']
        df1_boletos = df1_filtered[df1_filtered.iloc[:, 1].astype(str).str.contains('|'.join(palavras_chave), case=False, na=False)]

        # Identificar boletos sem correspondência
        boletos_sem_correspondencia = []
        df2_values = set(df2_filtered['value'].values) # Usar um set para buscas mais rápidas

        for index, row in df1_boletos.iterrows():
            value = row['value']
            if value not in df2_values:
                boletos_sem_correspondencia.append({
                    'Data': row['date'].strftime('%d/%m/%Y') if pd.notna(row['date']) else 'Data Inválida',
                    'Descrição': row[1],
                    'Valor': value
                })

        # Gerar relatório
        with open(tmp_report_path, 'w', encoding='utf-8') as f:
            f.write("Boletos pagos:\n\n")
            for data, descricao, valor in correspondencias:
                data_str = data.strftime('%d/%m/%Y') if pd.notna(data) else 'Data Inválida'
                f.write(f"Data: {data_str}, Descrição: {descricao}, Valor: {valor:.2f}\n")
            f.write(f"\nTotal de correspondências encontradas: {len(correspondencias)}\n")

            f.write("\nBoletos sem correspondência:\n\n")
            if boletos_sem_correspondencia:
                for boleto in boletos_sem_correspondencia:
                    f.write(f"Data: {boleto['Data']}, Descrição: {boleto['Descrição']}, Valor: {boleto['Valor']:.2f}\n")
            else:
                f.write("Nenhum boleto sem correspondência encontrado.\n")
            f.write(f"\nTotal de boletos sem correspondência: {len(boletos_sem_correspondencia)}")

        return send_file(
            tmp_report_path,
            as_attachment=True,
            download_name='relatorio_boletos.txt',
            mimetype='text/plain'
        )

    except Exception as e:
        logger.error(f"Erro ao processar os arquivos: {str(e)}", exc_info=True) # exc_info=True para logar o traceback
        return f"Erro ao processar os arquivos: {str(e)}", 500 # Usar 500 para erro interno do servidor

    finally:
        for path in (tmp_csv1_path, tmp_csv2_path, tmp_report_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    logger.warning(f"Falha ao remover arquivo temporário {path}")