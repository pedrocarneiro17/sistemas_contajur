# Novo arquivo: processadores/totais_processor.py

import re
import pandas as pd
import numpy as np

def process_totais_pdf(texto_completo):
    """
    Processa um PDF do modelo 'Relatório Totais de Notas e Cupons' e retorna:
    1. O DataFrame final com números ausentes preenchidos (se houver gaps na sequência).
    2. Uma lista de números ausentes.
    3. Um DataFrame contendo apenas os dados originais com valor, para comparação.
    
    Não aplica filtros adicionais; foca na extração de Número e V.NF para comparação com Excel.
    Assume números sequenciais para preenchimento de gaps (similar aos outros processadores).
    """
    dados = []
    linhas = texto_completo.split('\n')
    
    # Pular linhas de cabeçalho até encontrar o padrão de dados
    started = False
    for linha in linhas:
        linha_strip = linha.strip()
        if not started:
            # Padrão: número 6 dígitos, espaço, série '1', espaço, data YYYY-MM-DD
            if re.match(r'^\d{6}\s+1\s+\d{4}-\d{2}-\d{2}', linha_strip):
                started = True
        if started and re.match(r'^\d{6}\s+1\s+\d{4}-\d{2}-\d{2}', linha_strip):
            partes = linha_strip.split()
            if len(partes) == 8:  # Exato: Número, Série, Data, V.ICMS, V.ICMS.Sub, V.IPI, V.Produtos, V.NF
                numero = partes[0]
                serie = partes[1]
                data = partes[2]
                # Ignora as colunas intermediárias (V.ICMS, etc.), foca em V.NF para comparação
                vnf = float(partes[7])  # Extrai como float (formato US com ponto)
                dados.append([numero, serie, data, vnf])

    colunas = ['Número', 'Série', 'Data', 'V.NF']
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
            # Preenche com valores padrão para linhas ausentes
            df_ausentes = pd.DataFrame(numeros_ausentes, columns=['Número'])
            df_ausentes['Série'] = 1
            df_ausentes['Data'] = ''  # Sem data para ausentes
            df_ausentes['V.NF'] = 0.0
            df = pd.concat([df, df_ausentes], ignore_index=True)

        df = df.sort_values(by='Número').reset_index(drop=True)
    
    def formatar_valor(valor):
        if pd.isna(valor):
            return ''
        try:
            num = float(valor)
            return f"{num:.2f}".replace('.', ',')  # Padroniza para formato BR com vírgula
        except (ValueError, TypeError):
            return str(valor)
    
    df['V.NF'] = df['V.NF'].apply(formatar_valor)
    
    return df, numeros_ausentes, df_para_comparacao