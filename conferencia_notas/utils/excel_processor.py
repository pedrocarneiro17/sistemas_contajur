import pandas as pd
from io import BytesIO

def remove_duplicatas_e_vazias_xls(excel_file_content):
    """
    Lê um conteúdo de arquivo Excel, remove duplicatas com base no 'Nr. documento'
    e na 'Data de emissão', remove linhas vazias, e retorna
    o DataFrame processado e uma lista dos documentos duplicados removidos.
    """
    try:
        df = pd.read_excel(excel_file_content, engine='xlrd')

        # Verifica se as colunas necessárias existem
        if 'Nr. documento' not in df.columns:
            raise ValueError("A coluna 'Nr. documento' não foi encontrada no arquivo")
        if 'Data de emissão' not in df.columns:
            raise ValueError("A coluna 'Data de emissão' não foi encontrada no arquivo")

        # Remove as linhas completamente vazias
        df.dropna(how='all', inplace=True)

        # Encontra as duplicatas com base nas duas colunas
        duplicatas = df[df.duplicated(subset=['Nr. documento', 'Data de emissão'], keep='first')]
        documentos_removidos = duplicatas['Nr. documento'].tolist()

        # Remove as duplicatas, mantendo a primeira ocorrência
        df_sem_duplicatas = df.drop_duplicates(subset=['Nr. documento', 'Data de emissão'], keep='first')

        # Retorna o DataFrame e a lista de documentos removidos
        return df_sem_duplicatas, documentos_removidos

    except Exception as e:
        raise Exception(f"Erro ao processar o arquivo Excel: {str(e)}")