import re
import pandas as pd
import numpy as np

def process_sgbr_pdf(texto_completo):
    """
    Processa um PDF SGBr e retorna:
    1. O DataFrame final com números ausentes preenchidos.
    2. Uma lista de números ausentes.
    3. Um DataFrame contendo apenas os dados originais com valor, para comparação.
    """
    dados = []
    # Padrões regex para extração de dados
    numero_pattern = r'^\d{5}$'
    modelo_pattern = r'^\d{2}$'
    serie_pattern = r'^\d$'
    data_pattern = r'^(?:\d{2}/\d{2}/\d{4}|\d{4}:/\d{4}:/\d{6})$'
    total_pattern = r'^(?:R\$)?\s*[\d.,]+$'

    # Filtra linhas de cabeçalho, rodapé e outras informações irrelevantes
    linhas = texto_completo.split('\n')
    linhas_filtradas = [
        linha for linha in linhas
        if not (
            re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', linha.strip()) or
            any(keyword in linha.lower() for keyword in [
                'relatório', 'https', 'valor total', 'sgbr sistemas', 'status nfc-e:', 
                'totais', 'canceladas', 'rejeitadas', 'contingência', 'não enviadas', 'total líquido'
            ]) or
            "Número ModeloSérie" in linha
        )
    ]

    # Extrai os dados de cada linha válida
    for linha in linhas_filtradas:
        partes = linha.strip().split()
        if len(partes) >= 6:
            numero = partes[0] if re.match(numero_pattern, partes[0]) else None
            modelo = partes[1] if re.match(modelo_pattern, partes[1]) else None
            serie = partes[2] if re.match(serie_pattern, partes[2]) else None
            data = partes[-2] if re.match(data_pattern, partes[-2]) else None
            total = partes[-1] if re.match(total_pattern, partes[-1]) else None
            descricao = ' '.join(partes[3:-2]).strip()
            
            if total and total.startswith('R$'):
                total = total[2:].strip()
            
            if numero and modelo and serie and data and total:
                dados.append([numero, modelo, serie, descricao, data, total])

    colunas = ['Número', 'Modelo', 'Série', 'Descrição', 'Data emis.', 'Total nota']
    df = pd.DataFrame(dados, columns=colunas)

    if df.empty:
        return pd.DataFrame(columns=colunas), [], pd.DataFrame(columns=colunas)

    # Cria uma cópia para a comparação antes de qualquer modificação
    df_para_comparacao = df.copy()

    # Preenche os números ausentes
    numeros_ausentes = []
    df['Número'] = df['Número'].astype(int)
    min_numero, max_numero = df['Número'].min(), df['Número'].max()
    todos_numeros = set(range(min_numero, max_numero + 1))
    numeros_presentes = set(df['Número'])
    numeros_ausentes = sorted(list(todos_numeros - numeros_presentes))
    
    if numeros_ausentes:
        df_ausentes = pd.DataFrame(numeros_ausentes, columns=['Número'])
        df = pd.concat([df, df_ausentes], ignore_index=True)

    # Ordena e formata o DataFrame final
    df['Número'] = df['Número'].astype(int)
    df = df.sort_values(by='Número', ascending=True)
    df['Número'] = df['Número'].apply(lambda x: f'{x:05d}')
    df = df.drop_duplicates(subset=['Número'], keep='first').reset_index(drop=True)
    
    def formatar_valor(valor):
        if pd.isna(valor): return valor
        valor_str = str(valor).replace('.', '').replace(',', '.')
        try:
            num = float(valor_str)
            return f"{num:.2f}".replace('.', ',')
        except (ValueError, TypeError):
            return valor
    
    df['Total nota'] = df['Total nota'].apply(formatar_valor)
    
    return df, numeros_ausentes, df_para_comparacao
