import re
import pandas as pd
from io import BytesIO

def process_sgbr_pdf(texto_completo):
    """
    Processa um PDF do modelo SGBr, extrai a tabela, ordena por Número em ordem crescente,
    adiciona números ausentes, remove linhas duplicadas com base na coluna Número (mantendo a primeira)
    após ajustar toda a tabela, formata a coluna Total nota para usar vírgula como decimal,
    sem pontos nas casas de milhar, remove ,00 e zeros à direita, e remove R$ se presente,
    retornando um arquivo Excel em memória.
    """
    dados = []
    
    # Padrões regex para identificação das colunas
    numero_pattern = r'^\d{5}$'  # Exatamente 5 dígitos para Número (ajustado conforme dados)
    modelo_pattern = r'^\d{2}$'  # Exatamente 2 dígitos para Modelo
    serie_pattern = r'^\d$'      # Exatamente 1 dígito para Série
    data_pattern = r'^\d{2}/\d{2}/\d{4}$'  # DD/MM/YYYY
    total_pattern = r'^(?:R\$)?\d{1,3}(?:[,\.]\d{2})$'  # e.g., R$47,00, 293,80, aceita R$ opcional
    
    # Filtrar linhas indesejadas
    linhas = texto_completo.split('\n')
    linhas_filtradas = [
        linha for linha in linhas
        if not (
            re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', linha.strip()) or
            linha.strip().startswith('Relatório') or
            linha.strip().lower().startswith('https') or
            linha.strip().lower().startswith('valor total') or
            "Número ModeloSérie Natureza de operação CPF/CNPJ Chave de acesso Protocolo aut. Data emis. Total nota" in linha or
            "Número Modelo Série Natureza de operação CPF/CNPJ Chave de acesso Protocolo aut. Data emis. Total nota" in linha or
            linha.strip().startswith('SGBr Sistemas') or 
            linha.strip().startswith('Status NFC-e:') or 
            linha.strip().startswith('Número ModeloSérie') or
            linha.strip().startswith('Totais') or
            linha.strip().startswith('Canceladas') or
            linha.strip().startswith('Rejeitadas') or
            linha.strip().startswith('Contingência') or
            linha.strip().startswith('Não enviadas') or
            linha.strip().startswith('Total líquido')
        )
    ]
    
    # Processar linhas para o DataFrame
    for linha in linhas_filtradas:
        partes = linha.strip().split()
        if len(partes) >= 6:  # Mínimo de partes para uma linha válida
            numero = partes[0] if partes[0] and re.match(numero_pattern, partes[0]) else None
            modelo = partes[1] if partes[1] and re.match(modelo_pattern, partes[1]) else None
            serie = partes[2] if partes[2] and re.match(serie_pattern, partes[2]) else None
            data = partes[-2] if partes[-2] and re.match(data_pattern, partes[-2]) else None
            total = partes[-1] if partes[-1] and re.match(total_pattern, partes[-1]) else None
            descricao = ' '.join(partes[3:-2]).strip() if len(partes) > 6 else ''
            
            # Remover 'R$' do total, se presente
            if total and total.startswith('R$'):
                total = total[2:].strip()
            
            # Adicionar linha apenas se todos os campos obrigatórios forem válidos
            if numero and modelo and serie and data and total:
                dados.append([numero, modelo, serie, descricao, data, total])
    
    # Criar DataFrame
    colunas = ['Número', 'Modelo', 'Série', 'Descrição', 'Data emis.', 'Total nota']
    df = pd.DataFrame(dados, columns=colunas)
    
    # Converter 'Número' para inteiro para ordenação e preenchimento
    df['Número'] = df['Número'].astype(int)
    
    # Identificar números ausentes na sequência
    if not df.empty:
        min_numero = df['Número'].min()
        max_numero = df['Número'].max()
        todos_numeros = set(range(min_numero, max_numero + 1))
        numeros_presentes = set(df['Número'])
        numeros_ausentes = todos_numeros - numeros_presentes
        
        # Adicionar linhas para números ausentes com NaN
        for numero in numeros_ausentes:
            dados.append([f'{numero:05d}', 'NaN', 'NaN', 'NaN', 'NaN', 'NaN'])

    # Recriar DataFrame com números ausentes
    df = pd.DataFrame(dados, columns=colunas)
    
    # Ordenar por 'Número' em ordem crescente
    df['Número'] = df['Número'].astype(int)
    df = df.sort_values(by='Número', ascending=True)
    df['Número'] = df['Número'].apply(lambda x: f'{x:05d}')
    
    # Formatar a coluna 'Total nota' para remover ,00 e zeros à direita, usar vírgula como decimal, sem pontos nas casas de milhar
    def formatar_valor(valor):
        if pd.isna(valor):
            return 'NaN'  # Substituir NaN por NaN com letra maiúscula
        # Remover pontos de milhar e substituir vírgula por ponto para conversão numérica
        valor = valor.replace('.', '').replace(',', '.')
        try:
            num = float(valor)
            # Se for um número inteiro (termina em .0), remove os decimais
            if num.is_integer():
                return str(int(num))
            # Remove zeros à direita após o ponto decimal
            decimal_str = str(num).rstrip('0').rstrip('.')
            # Substituir ponto por vírgula para o formato desejado
            return decimal_str.replace('.', ',')
        except ValueError:
            return valor
    
    df['Total nota'] = df['Total nota'].apply(formatar_valor)
    
    # Remover linhas duplicadas com base na coluna 'Número', mantendo a primeira ocorrência, após ajustar a tabela
    df = df.drop_duplicates(subset=['Número'], keep='first')
    
    # Substituir todos os 'nan' por 'NaN' no DataFrame inteiro para consistência
    df = df.replace('nan', 'NaN')
    
    # Gerar Excel em memória
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return output