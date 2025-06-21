import re
from ..auxiliares.utils import process_transactions 
 
def preprocess_text(text):
    """
    Pré-processa o texto do extrato da LOFT DA SERRA LTDA para extrair transações, ignorando cabeçalho e rodapé.
    Combina o tipo de transação e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    Remove transações duplicadas (mesma data, descrição, valor e tipo).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    date_pattern = r"^(\d{2}/\d{2}/\d{4})$"
    value_pattern = r"([-]?\s*R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}\s*)$"  # Captura "- R$" ou "R$"
    
    transactions = []
    current_date = None
    
    for line in lines:
        # Ignorar linhas de cabeçalho
        if any(keyword in line.lower() for keyword in ["dados gerais", "nome agência/conta", "data horário", "extrato completo"]):
            continue
        
        # Verificar se a linha é uma data
        date_match = re.match(date_pattern, line)
        if date_match:
            current_date = date_match.group(1)
            continue
        
        # Ignorar linhas de saldo
        if any(keyword in line.lower() for keyword in ["saldo total dispon", "saldo do dia"]):
            continue
        
        # Processar linhas de transação
        value_match = re.search(value_pattern, line)
        if value_match and current_date:
            value = value_match.group(1).strip()
            tipo = "D" if "-" in value else "C"
            valor = value.replace("-", "").replace("R$", "").replace(" ", "").strip()
            
            # Ajustar valor: remover ",00" se for um número inteiro
            if valor.endswith(",00"):
                valor = valor[:-3]
            
            # Extrair descrição (remover ícones e valor)
            description = re.sub(r"[]", "", line).replace(value, "").strip()
            
            transactions.append({
                "Data": current_date,
                "Descrição": description,
                "Valor": valor,
                "Tipo": tipo
            })
    
    # Remover transações duplicadas
    seen = set()
    unique_transactions = []
    for transaction in transactions:
        # Criar uma tupla com os campos para verificar duplicatas
        transaction_tuple = (transaction["Data"], transaction["Descrição"], transaction["Valor"], transaction["Tipo"])
        if transaction_tuple not in seen:
            seen.add(transaction_tuple)
            unique_transactions.append(transaction)
    
    return unique_transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato da LOFT DA SERRA LTDA e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)