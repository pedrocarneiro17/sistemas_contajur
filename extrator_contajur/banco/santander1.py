import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Santander para extrair transações, ignorando cabeçalho e rodapé.
    Combina o histórico e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Padrão para identificar linhas de transação (começam com data DD/MM/YYYY)
    date_pattern = r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d{6})\s+([-]?\d{1,3}(?:\.\d{3})*,\d{2})(?:\s+[-]?\d{1,3}(?:\.\d{3})*,\d{2})?$'
    
    transactions = []
    
    for line in lines:
        # Ignorar linhas de cabeçalho ou rodapé
        if any(keyword in line for keyword in [
            "Aplicativo Santander", "Agência:", "Conta:", "Período:", "Data/Hora:", "Saldo disponível", 
            "Saldo de ContaMax", "Entenda a composição", "Central de Atendimento", "SAC", "Ouvidoria"
        ]):
            continue
        
        # Processar linhas de transação
        match = re.match(date_pattern, line)
        if match:
            data, historico, documento, valor = match.groups()[:4]
            # Determinar o tipo de transação (D para negativo, C para positivo)
            tipo = "D" if valor.startswith("-") else "C"
            # Remover o sinal de menos e formatar o valor
            valor = valor.replace("-", "").strip()
            # Ajustar valor: remover ",00" se for um número inteiro
            if valor.endswith(",00"):
                valor = valor[:-3]
            # Combinar histórico e documento na coluna Descrição
            description = f"{historico} {documento}".strip()
            
            transactions.append({
                "Data": data,
                "Descrição": description,
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
    """
    Processa o texto extraído do extrato do Santander e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)