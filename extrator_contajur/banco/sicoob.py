import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do Sicoob no formato estruturado do PyMuPDF.
    Extrai todas as informações necessárias e retorna os dados no formato final.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Extrair o ano do período (ex.: PERÍODO: 01/04/2025 - 30/04/2025)
    year = None
    period_pattern = r"PERÍODO:\s*\d{2}/\d{2}/(\d{4})\s*-\s*\d{2}/\d{2}/\d{4}"
    for line in lines:
        match = re.search(period_pattern, line)
        if match:
            year = match.group(1)
            break
    
    # Identificar início e fim das transações
    start_index = 0
    for i, line in enumerate(lines):
        if "DATA  HISTÓRICO  VALOR" in line:
            start_index = i + 1
            break
    
    end_index = len(lines)
    for i, line in enumerate(lines[start_index:], start=start_index):
        if "RESUMO" in line or "SALDO EM C.CORRENTE" in line:
            end_index = i
            break
    
    transaction_lines = lines[start_index:end_index]
    
    # Processar as transações
    data = []
    date_pattern = r"^(\d{2}/\d{2})\s*$"
    value_pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})([CD])?"
    type_pattern = r"^[CD]$"
    doc_pattern = r"DOC\.:"
    
    current_transaction = []
    in_transaction = False
    
    for line in transaction_lines:
        if re.match(date_pattern, line):
            # Processar transação anterior se existir
            if in_transaction and current_transaction:
                transaction_text = "\n".join(current_transaction)
                processed = _process_single_transaction(transaction_text, year, date_pattern, 
                                                      value_pattern, type_pattern, doc_pattern)
                if processed:
                    data.append(processed)
            
            # Começar nova transação
            current_transaction = [line]
            in_transaction = True
        elif in_transaction:
            current_transaction.append(line)
            if "DOC.:" in line or "SALDO DO DIA" in line or "SALDO ANTERIOR" in line or "SALDO BLOQ" in line:
                # Finalizar transação atual
                transaction_text = "\n".join(current_transaction)
                processed = _process_single_transaction(transaction_text, year, date_pattern,
                                                       value_pattern, type_pattern, doc_pattern)
                if processed:
                    data.append(processed)
                in_transaction = False
                current_transaction = []
    
    # Processar última transação se existir
    if in_transaction and current_transaction:
        transaction_text = "\n".join(current_transaction)
        processed = _process_single_transaction(transaction_text, year, date_pattern,
                                              value_pattern, type_pattern, doc_pattern)
        if processed:
            data.append(processed)
    
    return data

def _process_single_transaction(transaction, year, date_pattern, value_pattern, type_pattern, doc_pattern):
    """Função auxiliar para processar uma única transação"""
    lines = transaction.split("\n")
    
    # Ignorar transações de saldo
    if any(s in transaction for s in ["SALDO DO DIA", "SALDO ANTERIOR", "SALDO BLOQ"]):
        return None
    
    # Extrair data
    date_match = re.match(date_pattern, lines[0])
    if not date_match:
        return None
    date = date_match.group(1)
    if year:
        date = f"{date}/{year}"
    
    # Extrair valor e tipo
    value = None
    transaction_type = None
    value_line_index = None
    type_line_index = None
    
    for i, line in enumerate(lines[1:], start=1):
        value_match = re.match(value_pattern, line.strip())
        if value_match:
            value = value_match.group(1)
            value_line_index = i
            transaction_type = value_match.group(2)
            if not transaction_type and i + 1 < len(lines) and re.match(type_pattern, lines[i + 1].strip()):
                transaction_type = lines[i + 1].strip()
                type_line_index = i + 1
            break
    
    if not value or not transaction_type:
        return None
    
    if value.endswith(",00"):
        value = value[:-3]
    
    # Extrair descrição até o DOC.:
    doc_match = re.search(doc_pattern, transaction)
    if not doc_match:
        return None
    
    # Construir descrição, excluindo linhas de valor e tipo
    description_lines = []
    for i, line in enumerate(lines[1:], start=1):
        if i == value_line_index or i == type_line_index:
            continue
        if "DOC.:" in line:
            description_lines.append(line)
            break
        description_lines.append(line)
    
    description = " ".join(description_lines).strip()
    
    return {
        "Data": date,
        "Descrição": description,
        "Valor": value,
        "Tipo": transaction_type
    }

def extract_transactions(transactions):
    return transactions

def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)