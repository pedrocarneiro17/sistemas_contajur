import pandas as pd

def remove_duplicatas_e_vazias_xls(arquivo_entrada, arquivo_saida):
    try:
        # Lê o arquivo XLS usando xlrd (assumindo sempre .xls)
        df = pd.read_excel(arquivo_entrada, engine='xlrd')
        
        # Verifica se a coluna 'Nr. documento' existe
        if 'Nr. documento' not in df.columns:
            raise ValueError("A coluna 'Nr. documento' não foi encontrada no arquivo")
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Remove linhas duplicadas mantendo apenas a primeira ocorrência com base na coluna 'Nr. documento'
        df_sem_duplicatas = df.drop_duplicates(subset=['Nr. documento'], keep='first')
        
        # Salva o resultado em um novo arquivo XLSX
        df_sem_duplicatas.to_excel(arquivo_saida, index=False, engine='openpyxl')
        
        print(f"Arquivo processado com sucesso!")
        print(f"Linhas duplicadas removidas: {len(df) - len(df_sem_duplicatas)}")
        print(f"Linhas vazias removidas: {len(pd.read_excel(arquivo_entrada, engine='xlrd')) - len(df)}")
        print(f"Resultado salvo em: {arquivo_saida}")
        
    except FileNotFoundError:
        print(f"Erro: O arquivo {arquivo_entrada} não foi encontrado")
    except Exception as e:
        print(f"Erro ao processar o arquivo: {str(e)}")
