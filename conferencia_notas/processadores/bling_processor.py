import re
import pandas as pd
import numpy as np

def process_bling_pdf(texto_completo):
    """
    Processa um PDF Bling e retorna:
    1. O DataFrame final com números ausentes preenchidos.
    2. Uma lista de números ausentes.
    3. Um DataFrame contendo apenas os dados originais com valor, para comparação.
    """
    # ... (toda a lógica de extração de 'dados' continua a mesma) ...
    dados = []
    numero_pattern = r'^\d{6}$'
    tipo_pattern = r'^(Entrada|Saida|Saída)$'
    data_pattern = r'^\d{2}/\d{2}/\d{4}$'
    valor_pattern = r'^\d{1,3}(?:\.\d{3})*(?:[,\.]\d{2})$'
    linhas = texto_completo.split('\n')
    linhas_filtradas = [
        linha for linha in linhas
        if not (re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', linha.strip()) or any(s in linha.lower() for s in ['relatório', 'https', 'valor total']))
    ]
    for linha in linhas_filtradas:
        partes = linha.strip().split()
        if len(partes) >= 5:
            numero = partes[0] if re.match(numero_pattern, partes[0]) else None
            tipo = partes[1] if re.match(tipo_pattern, partes[1], re.IGNORECASE) else None
            data = partes[2] if re.match(data_pattern, partes[2]) else None
            if len(partes) >= 6 and partes[-3] == 'Emitida' and partes[-2] == 'DANFE':
                situacao = 'Emitida DANFE'
                valor = partes[-1] if re.match(valor_pattern, partes[-1].replace(' ', '')) else None
                cliente = ' '.join(partes[3:-3]).strip()
            elif len(partes) >= 5 and partes[-2] == 'Cancelada':
                situacao = 'Cancelada'
                valor = partes[-1] if re.match(valor_pattern, partes[-1].replace(' ', '')) else None
                cliente = ' '.join(partes[3:-2]).strip()
            else:
                situacao, valor, cliente = None, None, ''
            if numero and tipo and data and situacao and valor:
                if not cliente.lower().startswith('cliente'):
                    dados.append([numero, tipo, data, cliente, situacao, valor])

    colunas = ['Número', 'Tipo', 'Data emissão', 'Cliente', 'Situação', 'Valor']
    df = pd.DataFrame(dados, columns=colunas)

    # DataFrame para comparação (somente linhas que tinham valor originalmente)
    df_para_comparacao = df.copy()

    numeros_ausentes = []
    if not df.empty:
        df['Número'] = df['Número'].astype(int)
        min_numero, max_numero = df['Número'].min(), df['Número'].max()
        todos_numeros = set(range(min_numero, max_numero + 1))
        numeros_presentes = set(df['Número'])
        numeros_ausentes = sorted(list(todos_numeros - numeros_presentes))
        
        if numeros_ausentes:
            df_ausentes = pd.DataFrame(numeros_ausentes, columns=['Número'])
            df = pd.concat([df, df_ausentes], ignore_index=True)

        df['Número'] = df['Número'].astype(int)
        df = df.sort_values(by='Número').reset_index(drop=True)
        df['Número'] = df['Número'].apply(lambda x: f'{int(x):06d}')
    
    def formatar_valor(valor):
        if pd.isna(valor): return valor
        valor_str = str(valor).replace('.', '').replace(',', '.')
        try:
            num = float(valor_str)
            return f"{num:.2f}".replace('.', ',') # Padroniza para duas casas decimais
        except (ValueError, TypeError):
            return valor
    
    df['Valor'] = df['Valor'].apply(formatar_valor)
    
    return df, numeros_ausentes, df_para_comparacao
