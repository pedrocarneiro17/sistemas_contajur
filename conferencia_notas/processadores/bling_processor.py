import re
import pandas as pd
from io import BytesIO
import numpy as np

def process_bling_pdf(texto_completo):
    """
    Processa um PDF do modelo Bling, extrai a tabela, mantém a ordem original dos dados,
    adiciona números ausentes na sequência com NaN em todas as colunas (inclusive Valor),
    formata a coluna Valor para remover ,00 e zeros à direita, usa vírgula como decimal,
    sem pontos nas casas de milhar, e adiciona ' #' ao final,
    e retorna o Excel em memória.
    """
    dados = []
    
    # Padrões regex para identificação das colunas
    numero_pattern = r'^\d{6}$'  # Exatamente 6 dígitos para Número
    tipo_pattern = r'^(Entrada|Saida|Saída)$'  # Entrada ou Saída (permite erro de OCR "Saida")
    data_pattern = r'^\d{2}/\d{2}/\d{4}$'  # DD/MM/YYYY
    situacao_pattern = r'^(Emitida\s*DANFE|Cancelada)$'  # Emitida DANFE ou Cancelada
    valor_pattern = r'^\d{1,3}(?:\.\d{3})*(?:[,\.]\d{2})$'  # e.g., 1.259,00, 946,28, 0,00
    
    # Filtrar linhas indesejadas
    linhas = texto_completo.split('\n')
    linhas_filtradas = [
        linha for linha in linhas
        if not (
            re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', linha.strip()) or
            linha.strip().startswith('Relatório') or
            linha.strip().lower().startswith('https') or
            linha.strip().lower().startswith('valor total')
        )
    ]
    
    # Processar linhas para o DataFrame
    for linha in linhas_filtradas:
        partes = linha.strip().split()
        if len(partes) >= 5:  # Mínimo de partes para uma linha válida
            numero = partes[0] if partes[0] and re.match(numero_pattern, partes[0]) else None
            tipo = partes[1] if partes[1] and re.match(tipo_pattern, partes[1], re.IGNORECASE) else None
            data = partes[2] if partes[2] and re.match(data_pattern, partes[2]) else None
            
            # Verificar Situação: "Emitida DANFE" (duas partes) ou "Cancelada" (uma parte)
            if len(partes) >= 6 and partes[-3] == 'Emitida' and partes[-2] == 'DANFE':
                situacao = 'Emitida DANFE'
                valor = partes[-1] if partes[-1] else None
                cliente = ' '.join(partes[3:-3]).strip() if len(partes) > 6 else ''
            elif partes[-2] and re.match(r'^Cancelada$', partes[-2]):
                situacao = 'Cancelada'
                valor = partes[-1] if partes[-1] else None
                cliente = ' '.join(partes[3:-2]).strip() if len(partes) > 5 else ''
            else:
                situacao = None
                valor = None
                cliente = ''
                print(f"Falha ao combinar Situação em linha: {linha}")
            
            # Validar o valor com regex, mas manter como string
            if valor and not re.match(valor_pattern, valor.replace(' ', '')):
                print(f"Falha ao combinar Valor: '{valor}' em linha: {linha}")
                valor = None
            
            # Adicionar linha apenas se todos os campos obrigatórios forem válidos
            if numero and tipo and data and situacao and valor:
                if cliente and not cliente.lower().startswith('cliente'):
                    dados.append([numero, tipo, data, cliente, situacao, valor])
    
    # Criar DataFrame
    colunas = ['Número', 'Tipo', 'Data emissão', 'Cliente', 'Situação', 'Valor']
    df = pd.DataFrame(dados, columns=colunas)
    
    # Converter 'Número' para inteiro para identificar números ausentes
    if df.empty:
        print("Nenhum dado válido encontrado no texto.")
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        return output
    
    df['Número'] = df['Número'].astype(int)
    
    # Identificar números ausentes na sequência
    min_numero = df['Número'].min()
    max_numero = df['Número'].max()
    todos_numeros = set(range(min_numero, max_numero + 1))
    numeros_presentes = set(df['Número'])
    numeros_ausentes = todos_numeros - numeros_presentes
    
    # Adicionar linhas para números ausentes com NaN
    for numero in numeros_ausentes:
        dados.append([f'{numero:06d}', np.nan, np.nan, np.nan, np.nan, np.nan])
    
    # Recriar DataFrame com números ausentes, mantendo a ordem original
    df = pd.DataFrame(dados, columns=colunas)
    
    # Garantir que 'Número' seja string com 6 dígitos
    df['Número'] = df['Número'].apply(lambda x: f'{int(x):06d}' if pd.notnull(x) else x)
    
    # Formatar a coluna 'Valor' para remover ,00 e zeros à direita, usar vírgula como decimal, sem pontos nas casas de milhar, e adicionar ' #'
    def formatar_valor(valor):
        if pd.isna(valor):
            return valor
        # Remover pontos de milhar e substituir vírgula por ponto para conversão numérica
        valor = valor.replace('.', '').replace(',', '.')
        try:
            num = float(valor)
            # Se for um número inteiro (termina em .0), remove os decimais
            if num.is_integer():
                return f"{int(num)}"
            # Remove zeros à direita após o ponto decimal
            decimal_str = str(num).rstrip('0').rstrip('.')
            # Substituir ponto por vírgula para o formato desejado
            return decimal_str.replace('.', ',')
        except ValueError:
            return valor
    
    df['Valor'] = df['Valor'].apply(formatar_valor)
    
    # Gerar Excel em memória
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return output