import re
import pandas as pd
from io import BytesIO
import numpy as np

def process_fechamento_pdf(texto_completo):
    """
    Processa um texto extraído de um PDF fiscal, extrai dados das seções 'Operação: SAÍDAS Modelo: 55'
    e 'Operação: SAÍDAS Modelo: 65', agrupa por "N° NF" somando "Total NF" e mantém a primeira ocorrência,
    ordena por "N° NF" na sequência correta, preenchendo lacunas com NaN, formatando "Total NF"
    com vírgula como decimal, sem pontos nas casas de milhar e removendo ,00 e zeros à direita,
    retornando um arquivo Excel em memória.
    """
    dados = []
    colunas = [
        "Data", "N° NF", "CFOP", "Razão Social / Nome Destinatário",
        "CST/CSOSN", "Valor ICMS", "Total NF", "Nat. Op.", "Modelo"
    ]

    # Encontrar as posições das seções
    inicio_saidas_55 = texto_completo.find("Operação: SAÍDAS Modelo: 55")
    if inicio_saidas_55 == -1:
        print("Seção 'Operação: SAÍDAS Modelo: 55' não encontrada no texto.")
        df = pd.DataFrame(columns=colunas)
    else:
        # Encontrar a SEGUNDA ocorrência de "Operação: SAÍDAS Modelo: 65"
        primeira_ocorrencia_65 = texto_completo.find("Operação: SAÍDAS Modelo: 65")
        segunda_ocorrencia_65 = texto_completo.find("Operação: SAÍDAS Modelo: 65", primeira_ocorrencia_65 + 1)
        
        # Extrair o texto entre a primeira ocorrência de 55 e a segunda de 65
        if segunda_ocorrencia_65 != -1:
            texto_secao = texto_completo[inicio_saidas_55:segunda_ocorrencia_65]
        else:
            texto_secao = texto_completo[inicio_saidas_55:]
        
        # Dividir o texto em linhas
        linhas = texto_secao.split('\n')
        
        # Padrões para filtragem
        padrao_cst_csosn = re.compile(r'^(CST/|CSOSN)')
        padrao_cabecalho = re.compile(r'^Data\s+N°\s+NF\s+CFOP\s+Razão\s+Social\s+/\s+Nome\s+Destinatário\s+Valor\s+ICMS\s+Total\s+NF\s+Nat\.\s+Op\.$')
        padrao_totais = re.compile(r'^Totais:')
        padrao_xx_de_xx = re.compile(r'^\d+\s+de\s+\d+$')
        padrao_periodo = re.compile(r'^Período:')
        padrao_cnpj_data_hora = re.compile(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+Data: \d{2}/\d{2}/\d{4} Hora: \d{2}:\d{2}:\d{2}$')
        padrao_cfop_descricao = re.compile(r'^CFOP\s+DESC\s+R\s+I\s+Ç\s+Ã\s+O\s+ICMS\s+Total$')
        padrao_relatorio = re.compile(r'^Relatório Fechamento Fiscal CFOP\'s$')
        padrao_entradas = re.compile(r'^Operação: ENTRADAS Modelo: 55$')
        padrao_saidas_65 = re.compile(r'^Operação: SAÍDAS Modelo: 65$')
        
        # Filtrar linhas e rastrear modelo
        linhas_filtradas = []
        modelo_atual = "55"
        i = 0
        contador_saidas_65 = 0
        while i < len(linhas):
            if padrao_saidas_65.match(linhas[i]):
                modelo_atual = "65"
                contador_saidas_65 += 1
                if contador_saidas_65 == 2:
                    break
                i += 1
                continue
            
            if padrao_relatorio.match(linhas[i]) or padrao_entradas.match(linhas[i]):
                i += 1
                continue
            
            if (padrao_cst_csosn.match(linhas[i]) or
                padrao_cabecalho.match(linhas[i]) or
                padrao_totais.match(linhas[i]) or
                padrao_xx_de_xx.match(linhas[i]) or
                padrao_periodo.match(linhas[i])):
                i += 1
                continue
            if padrao_cnpj_data_hora.match(linhas[i]) or padrao_cfop_descricao.match(linhas[i]):
                i += 2
                continue
            
            linhas_filtradas.append((linhas[i], modelo_atual))
            i += 1
        
        # Processar as linhas filtradas para extrair os dados
        padrao_linha = re.compile(
            r'^(\d{2}/\d{2}/\d{4})\s+'    # Data
            r'(\d+)\s+'                    # N° NF
            r'(\d{4})\s+'                  # CFOP
            r'(.*?)?\s*'                   # Razão Social (opcional, pode ser vazio)
            r'(\d{3,5})\s+'                # CST/CSOSN
            r'R\$\s+([\d.,]+)\s+'          # Valor ICMS
            r'R\$\s+([\d.,]+)\s+'          # Total NF
            r'(NOTA FISCAL.*|CUPOM FISCAL.*)$'  # Nat. Op.
        )
        
        for linha, modelo in linhas_filtradas:
            linha = linha.strip()
            if not linha or not re.match(r'^\d{2}/\d{2}/\d{4}', linha):
                continue
            
            match = padrao_linha.match(linha)
            if match:
                groups = list(match.groups())
                groups[3] = groups[3].strip() if groups[3] is not None else ''
                groups.append(modelo)
                dados.append(groups)
        
        # Criar DataFrame
        df = pd.DataFrame(dados, columns=colunas)
    
    # Agrupar por "N° NF" e somar "Total NF", mantendo a primeira ocorrência
    if not df.empty:
        # Converter "Total NF" para numérico, removendo R$
        df['Total NF'] = df['Total NF'].replace('R\$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.').astype(float)
        # Agrupar por "N° NF", somando "Total NF" e mantendo a primeira ocorrência dos outros campos
        df_agg = df.groupby('N° NF').agg({
            'Data': 'first',
            'CFOP': 'first',
            'Razão Social / Nome Destinatário': 'first',
            'CST/CSOSN': 'first',
            'Valor ICMS': 'first',
            'Total NF': 'sum',
            'Nat. Op.': 'first',
            'Modelo': 'first'
        }).reset_index()
        # Formatar "Total NF" com vírgula como decimal, sem pontos nas casas de milhar, removendo ,00 e zeros à direita
        def formatar_valor(valor):
            if pd.isna(valor):
                return valor
            try:
                num = float(valor)
                if num.is_integer():
                    return str(int(num))
                decimal_str = str(num).rstrip('0').rstrip('.')
                return decimal_str.replace('.', ',')
            except ValueError:
                return valor
        df_agg['Total NF'] = df_agg['Total NF'].apply(formatar_valor)
    else:
        df_agg = df

    # Ordenar por "Modelo" (55 antes de 65) e "N° NF" e preencher lacunas
    if not df_agg.empty:
        # Garantir que "N° NF" seja do tipo int para consistência
        df_agg['N° NF'] = df_agg['N° NF'].astype(int)

        # Separar por modelo
        df_55 = df_agg[df_agg['Modelo'] == '55'].copy()
        df_65 = df_agg[df_agg['Modelo'] == '65'].copy()

        # Preencher lacunas para Modelo 55
        if not df_55.empty:
            min_nf_55 = df_55['N° NF'].min()
            max_nf_55 = df_55['N° NF'].max()
            all_nf_55 = pd.DataFrame({'N° NF': range(int(min_nf_55), int(max_nf_55) + 1)})
            all_nf_55['N° NF'] = all_nf_55['N° NF'].astype(int)
            df_55_full = pd.merge(all_nf_55, df_55, on='N° NF', how='left', sort=False)
        else:
            df_55_full = pd.DataFrame(columns=colunas)

        # Preencher lacunas para Modelo 65
        if not df_65.empty:
            min_nf_65 = df_65['N° NF'].min()
            max_nf_65 = df_65['N° NF'].max()
            all_nf_65 = pd.DataFrame({'N° NF': range(int(min_nf_65), int(max_nf_65) + 1)})
            all_nf_65['N° NF'] = all_nf_65['N° NF'].astype(int)
            df_65_full = pd.merge(all_nf_65, df_65, on='N° NF', how='left', sort=False)
        else:
            df_65_full = pd.DataFrame(columns=colunas)

        # Concatenar os DataFrames, mantendo Modelo 55 antes de 65
        df_full = pd.concat([df_55_full, df_65_full], ignore_index=True)

        # Ordenar apenas por "N° NF" para manter a sequência natural, com NaN no final
        df_full = df_full.sort_values(by='N° NF', na_position='last')

        # Preencher NaN nos campos que não foram mapeados
        df_full[colunas] = df_full[colunas].fillna(np.nan)
    else:
        df_full = df_agg

    # Gerar Excel em memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_full.to_excel(writer, index=False, sheet_name="SAÍDAS")
        ws = writer.sheets["SAÍDAS"]
        
        # Ajustar largura das colunas
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2) * 1.2
            ws.column_dimensions[column].width = adjusted_width
    
    output.seek(0)
    print("Dados processados com sucesso.")
    return output