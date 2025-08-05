import pandas as pd
from io import BytesIO

def remove_duplicatas_e_vazias_xls(excel_file_content):
    """
    Lê um conteúdo de arquivo Excel, remove duplicatas e vazias, e retorna
    o DataFrame processado e uma lista dos documentos duplicados removidos.
    """
    try:
        df = pd.read_excel(excel_file_content, engine='xlrd')
        
        if 'Nr. documento' not in df.columns:
            raise ValueError("A coluna 'Nr. documento' não foi encontrada no arquivo")
        
        df.dropna(how='all', inplace=True)
        
        duplicatas = df[df.duplicated(subset=['Nr. documento'], keep='first')]
        documentos_removidos = duplicatas['Nr. documento'].tolist()
        
        df_sem_duplicatas = df.drop_duplicates(subset=['Nr. documento'], keep='first')
        
        # Retorna o DataFrame e a lista de documentos removidos
        return df_sem_duplicatas, documentos_removidos
        
    except Exception as e:
        raise Exception(f"Erro ao processar o arquivo Excel: {str(e)}")
