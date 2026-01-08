import os
from flask import Blueprint, request, send_file, render_template
import pandas as pd
import tempfile
import logging
import zipfile
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

entrada_saida_bp = Blueprint('entrada_saida', __name__, url_prefix='/entrada_saida',
                              template_folder='templates', static_folder='static')


def processar_csv_entrada_saida(arquivo_csv):
    """
    Processa o CSV aplicando os critérios de exclusão:
    1. Remove linhas com valor 0,01 na coluna Valor
    2. Remove pares únicos de Entrada/Saída com mesmo valor
    """
    
    # Ler o CSV com encoding correto e separador ponto e vírgula
    try:
        df = pd.read_csv(arquivo_csv, encoding='latin1', sep=';')
        logger.info(f"CSV lido com sucesso usando encoding latin1")
    except Exception as e1:
        try:
            df = pd.read_csv(arquivo_csv, encoding='iso-8859-1', sep=';')
            logger.info(f"CSV lido com sucesso usando encoding iso-8859-1")
        except Exception as e2:
            try:
                df = pd.read_csv(arquivo_csv, encoding='cp1252', sep=';')
                logger.info(f"CSV lido com sucesso usando encoding cp1252")
            except Exception as e3:
                logger.error(f"Erro ao ler CSV com todos os encodings: {e1}, {e2}, {e3}")
                raise
    
    # Limpar espaços em branco das colunas
    df.columns = df.columns.str.strip()
    
    logger.info(f"Colunas encontradas: {df.columns.tolist()}")
    logger.info(f"Total de linhas no arquivo original: {len(df)}")
    
    # Verificar se a coluna Valor existe
    if 'Valor' not in df.columns:
        raise ValueError("Coluna 'Valor' não encontrada no arquivo")
    
    # Converter coluna Valor de string para float
    # No formato brasileiro: 1.012,87
    # 1. Remover pontos (separador de milhar)
    # 2. Substituir vírgula por ponto (separador decimal)
    # 3. Converter para float
    df['Valor'] = df['Valor'].astype(str).str.replace('.', '', regex=False)
    df['Valor'] = df['Valor'].str.replace(',', '.', regex=False)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # Remover linhas com valores NaN na coluna Valor
    linhas_com_nan = df['Valor'].isna().sum()
    if linhas_com_nan > 0:
        logger.warning(f"Removendo {linhas_com_nan} linhas com valores inválidos na coluna Valor")
    df = df.dropna(subset=['Valor'])
    
    # Critério 1: Remover linhas com valor 0,01 na coluna Valor
    linhas_antes = len(df)
    df = df[df['Valor'] != 0.01]
    linhas_removidas_001 = linhas_antes - len(df)
    logger.info(f"Linhas removidas com valor 0,01: {linhas_removidas_001}")
    
    # Verificar se a coluna Tipo de lançamento existe
    if 'Tipo de lançamento' not in df.columns:
        logger.warning("Coluna 'Tipo de lançamento' não encontrada. Pulando remoção de pares.")
        # Formatar valores de volta para o padrão brasileiro
        df['Valor'] = df['Valor'].apply(formatar_brasileiro)
        return df
    
    # Critério 2: Remover pares únicos de Entrada/Saída
    linhas_para_remover = set()
    
    # Limpar espaços da coluna Tipo de lançamento
    df['Tipo de lançamento'] = df['Tipo de lançamento'].astype(str).str.strip()
    
    # Agrupar por valor
    valores_unicos = df['Valor'].unique()
    
    for valor in valores_unicos:
        # Filtrar linhas com esse valor
        linhas_valor = df[df['Valor'] == valor]
        
        # Contar quantas entradas e saídas existem
        entradas = linhas_valor[linhas_valor['Tipo de lançamento'] == 'Entrada']
        saidas = linhas_valor[linhas_valor['Tipo de lançamento'] == 'Saída']
        
        qtd_entradas = len(entradas)
        qtd_saidas = len(saidas)
        
        # Se tiver exatamente 1 entrada e 1 saída com o mesmo valor, marca para remoção
        if qtd_entradas == 1 and qtd_saidas == 1:
            linhas_para_remover.add(entradas.index[0])
            linhas_para_remover.add(saidas.index[0])
            logger.info(f"Removendo par com valor {valor:.2f}")
    
    # Remover as linhas marcadas
    pares_removidos = len(linhas_para_remover) // 2
    logger.info(f"Total de pares removidos: {pares_removidos}")
    
    df_final = df.drop(index=list(linhas_para_remover))
    
    logger.info(f"Linhas finais: {len(df_final)}")
    
    # Formatar valores de volta para o padrão brasileiro
    df_final['Valor'] = df_final['Valor'].apply(formatar_brasileiro)
    
    return df_final


def formatar_brasileiro(valor):
    """Formata número para padrão brasileiro (1.012,87)"""
    valor_str = f"{valor:.2f}"
    partes = valor_str.split('.')
    inteiro = partes[0]
    decimal = partes[1]
    
    # Adicionar separador de milhar
    inteiro_formatado = ''
    for i, digito in enumerate(reversed(inteiro)):
        if i > 0 and i % 3 == 0:
            inteiro_formatado = '.' + inteiro_formatado
        inteiro_formatado = digito + inteiro_formatado
    
    return f"{inteiro_formatado},{decimal}"


@entrada_saida_bp.route('/')
def entrada_saida_page():
    return render_template('entrada_saida.html')


@entrada_saida_bp.route('/upload', methods=['POST'])
def upload_csvs():
    if 'csvs' not in request.files:
        logger.error("Nenhum arquivo 'csvs' fornecido.")
        return "Erro: Nenhum arquivo fornecido.", 400

    uploaded_files = request.files.getlist('csvs')
    if not uploaded_files:
        logger.error("Nenhum arquivo selecionado para upload.")
        return "Erro: Nenhum arquivo selecionado.", 400

    # Validar extensões
    for file in uploaded_files:
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext != '.csv':
                return f"Erro: O arquivo '{file.filename}' não é um arquivo CSV válido.", 400

    temp_files_to_clean = []
    processed_files = []

    try:
        # Processar cada CSV
        for csv_file in uploaded_files:
            if csv_file.filename == '':
                continue

            # Salvar arquivo temporário de entrada
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_csv:
                tmp_csv.write(csv_file.read())
                tmp_csv_path = tmp_csv.name
                temp_files_to_clean.append(tmp_csv_path)
                logger.info(f"Arquivo CSV '{csv_file.filename}' salvo temporariamente como: {tmp_csv_path}")

            try:
                # Processar o CSV
                df_processado = processar_csv_entrada_saida(tmp_csv_path)
                
                # Salvar CSV processado com o MESMO NOME do original
                output_filename = csv_file.filename
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', encoding='utf-8-sig') as tmp_output:
                    output_path = tmp_output.name
                    temp_files_to_clean.append(output_path)
                
                # Salvar como CSV com separador ponto e vírgula
                df_processado.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
                    
                processed_files.append((output_path, output_filename))
                logger.info(f"Arquivo '{csv_file.filename}' processado com sucesso. Linhas finais: {len(df_processado)}")
                
            except Exception as e:
                logger.error(f"Erro ao processar {csv_file.filename}: {e}")
                continue

        if not processed_files:
            return "Erro: Nenhum arquivo foi processado com sucesso. Verifique os logs do servidor.", 400

        # Se for apenas 1 arquivo, retornar o CSV direto
        if len(processed_files) == 1:
            file_path, file_name = processed_files[0]
            logger.info(f"Retornando arquivo único: {file_name}")
            return send_file(file_path, as_attachment=True, download_name=file_name, mimetype='text/csv')

        # Se for mais de 1 arquivo, criar ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path, file_name in processed_files:
                zip_file.write(file_path, file_name)
                logger.info(f"Arquivo '{file_name}' adicionado ao ZIP.")

        zip_buffer.seek(0)

        # Salvar ZIP temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            tmp_zip.write(zip_buffer.read())
            final_zip_path = tmp_zip.name
            temp_files_to_clean.append(final_zip_path)

        logger.info(f"ZIP criado com sucesso: {final_zip_path}")
        
        return send_file(final_zip_path, as_attachment=True, download_name="csvs_processados.zip", mimetype='application/zip')

    finally:
        # Limpar arquivos temporários
        for path in temp_files_to_clean:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.info(f"Arquivo temporário removido: {path}")
                except Exception as e:
                    logger.warning(f"Falha ao remover arquivo temporário {path}: {e}")