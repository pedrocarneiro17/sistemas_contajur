import re
import pandas as pd
import numpy as np

def process_fechamento_pdf(texto_completo):
    """
    Processa um PDF fiscal e retorna:
    1. O DataFrame final com NFs ausentes preenchidas.
    2. Uma lista de NFs ausentes.
    3. Um DataFrame contendo os dados agregados originais para comparação.
    """
    dados = []
    colunas = ["Data", "N° NF", "CFOP", "Razão Social / Nome Destinatário", "CST/CSOSN", "Valor ICMS", "Total NF", "Nat. Op.", "Modelo"]

    inicio_saidas_55 = texto_completo.find("Operação: SAÍDAS Modelo: 55")
    if inicio_saidas_55 == -1:
        return pd.DataFrame(columns=colunas), [], pd.DataFrame(columns=colunas)

    primeira_ocorrencia_65 = texto_completo.find("Operação: SAÍDAS Modelo: 65")
    segunda_ocorrencia_65 = texto_completo.find("Operação: SAÍDAS Modelo: 65", primeira_ocorrencia_65 + 1)
    texto_secao = texto_completo[inicio_saidas_55:segunda_ocorrencia_65] if segunda_ocorrencia_65 != -1 else texto_completo[inicio_saidas_55:]
    
    linhas = texto_secao.split('\n')
    padrao_linha = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d{4})\s+(.*?)?\s*(\d{3,5})\s+R\$\s+([\d.,]+)\s+R\$\s+([\d.,]+)\s+(NOTA FISCAL.*|CUPOM FISCAL.*)$')
    
    modelo_atual = "55"
    for linha in linhas:
        if "Operação: SAÍDAS Modelo: 65" in linha:
            modelo_atual = "65"
            continue
        match = padrao_linha.match(linha.strip())
        if match:
            groups = list(match.groups())
            groups[3] = groups[3].strip() if groups[3] is not None else ''
            groups.append(modelo_atual)
            dados.append(groups)
            
    df = pd.DataFrame(dados, columns=colunas)
    
    if df.empty:
        return pd.DataFrame(columns=colunas), [], pd.DataFrame(columns=colunas)

    df['Total NF'] = df['Total NF'].replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.').astype(float)
    df_agg = df.groupby('N° NF').agg({
        'Data': 'first', 'CFOP': 'first', 'Razão Social / Nome Destinatário': 'first',
        'CST/CSOSN': 'first', 'Valor ICMS': 'first', 'Total NF': 'sum',
        'Nat. Op.': 'first', 'Modelo': 'first'
    }).reset_index()
    df_agg['N° NF'] = df_agg['N° NF'].astype(int)
    
    df_para_comparacao = df_agg.copy()

    df_55 = df_agg[df_agg['Modelo'] == '55'].copy()
    df_65 = df_agg[df_agg['Modelo'] == '65'].copy()
    
    df_final_list = []
    numeros_ausentes_geral = []

    for df_modelo in [df_55, df_65]:
        if not df_modelo.empty:
            min_nf, max_nf = int(df_modelo['N° NF'].min()), int(df_modelo['N° NF'].max())
            all_nf_range = set(range(min_nf, max_nf + 1))
            numeros_presentes = set(df_modelo['N° NF'])
            
            numeros_ausentes_modelo = sorted(list(all_nf_range - numeros_presentes))
            numeros_ausentes_geral.extend(numeros_ausentes_modelo)
            
            df_full_modelo = pd.DataFrame({'N° NF': sorted(list(all_nf_range))})
            df_full_modelo = pd.merge(df_full_modelo, df_modelo, on='N° NF', how='left')
            
            df_final_list.append(df_full_modelo)

    if df_final_list:
        df_full = pd.concat(df_final_list, ignore_index=True)
        df_full = df_full.sort_values(by=['Modelo', 'N° NF']).reset_index(drop=True)
        for col in colunas:
            if col not in df_full.columns:
                df_full[col] = np.nan
        df_full = df_full[colunas]
    else:
        df_full = df_agg

    def formatar_valor_final(valor):
        if pd.isna(valor): return valor
        try:
            num = float(valor)
            return f"{num:.2f}".replace('.', ',')
        except (ValueError, TypeError):
            return valor
            
    df_full['Total NF'] = df_full['Total NF'].apply(formatar_valor_final)

    return df_full, sorted(numeros_ausentes_geral), df_para_comparacao
