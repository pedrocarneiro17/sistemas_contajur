import re
from ..auxiliares.utils import process_transactions  

def preprocess_text(text):
    """
    Processa o texto do extrato Cora, extraindo e formatando transações.
    Retorna uma lista de dicionários com Data, Descrição, Valor e Tipo.
    """
    # Dividir o texto em linhas
    linhas = text.splitlines()
    transacoes = []
    ultima_data = None
    encontrou_transacoes = False
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}')
    value_pattern = re.compile(r'[+-]\s*R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}')
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        if linha == "Transações":
            encontrou_transacoes = True
            continue
        if not encontrou_transacoes:
            continue
        if linha.startswith("Cora SCFI") or linha.startswith("Ouvidoria") or linha.startswith("Extrato gerado"):
            continue
        
        # Verificar se a linha começa com uma data
        if date_pattern.match(linha):
            # Atualizar a última data válida
            ultima_data = linha.split()[0]
            continue
        
        # Verificar se é uma transação (contém + R$ ou - R$)
        if value_pattern.search(linha):
            if not ultima_data:
                continue  # Ignorar transações sem data associada
            # Extrair valor
            valor_match = value_pattern.search(linha)
            valor_str = valor_match.group(0)
            # Determinar tipo
            tipo = 'C' if '+ R$' in valor_str else 'D'
            # Formatando valor
            valor = valor_str.replace('+ R$', '').replace('- R$', '').strip()
            if valor.endswith(",00"):
                valor = valor[:-3]
            elif valor.endswith("0"):
                valor = valor[:-1]
            # Extrair descrição
            descricao = linha.replace(valor_str, '').strip()
            # Adicionar transação
            transacoes.append({
                "Data": ultima_data,
                "Descrição": descricao,
                "Valor": valor,
                "Tipo": tipo
            })
    
    return transacoes

def extract_transactions(transactions):
    """
    Retorna a lista de transações (mantido para compatibilidade).
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato Cora e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)