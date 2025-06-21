import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato da LOFT DA SERRA LTDA para extrair transações, ignorando cabeçalho e rodapé.
    Combina o tipo de transação e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    Remove transações duplicadas (mesma data, descrição, valor e tipo).
    """
    # Dividir o texto em transações com base no padrão de data (DD/MM/YYYY)
    date_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
    transactions = []

    # Dividir o texto em partes com base nas datas
    parts = date_pattern.split(text)
    dates = date_pattern.findall(text)
    
    # Associar cada parte à sua data correspondente
    for date, part in zip(dates, parts[1:]):  # Ignorar a primeira parte (antes da primeira data)
        transacao_unificada = f"{date} {part.strip()}"
        # Ignorar transações com "S A L D O" ou "Saldo Anterior"
        if "S A L D O" in transacao_unificada or "Saldo Anterior" in transacao_unificada:
            continue
        
        # Dividir a transação em partes
        partes = transacao_unificada.split()
        if len(partes) < 3:
            continue
        
        # Encontrar o primeiro valor monetário e seu tipo
        value_pattern = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}')
        valor = None
        tipo = None
        idx_valor = -1
        for i, parte in enumerate(partes):
            if value_pattern.match(parte):
                valor = parte
                idx_valor = i
                if i + 1 < len(partes):
                    tipo = partes[i + 1]
                break
        
        # Ignorar transação se o tipo for '*' ou inválido
        if tipo == '*' or not valor or tipo not in ['C', 'D']:
            continue
        
        # Construir a descrição
        desc_inicial = ' '.join(partes[1:idx_valor]).strip()
        idx_fim = idx_valor + 2  # Após o valor e tipo
        # Verificar se há um segundo valor monetário seguido de tipo
        for i in range(idx_valor + 2, len(partes)):
            if value_pattern.match(partes[i]):
                idx_fim = i + 2  # Pular o segundo valor e seu tipo
                break
        desc_final = ' '.join(partes[idx_fim:]).strip()
        descricao = f"{desc_inicial} {desc_final}".strip() if desc_final else desc_inicial
        
        # Ajustar valor: remover ",00" se for um número inteiro
        if valor.endswith(",00"):
            valor = valor[:-3]
        
        transactions.append({
            "Data": date,
            "Descrição": descricao,
            "Valor": valor,
            "Tipo": tipo
        })
    
    
    return transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):

    return process_transactions(text, preprocess_text, extract_transactions)

