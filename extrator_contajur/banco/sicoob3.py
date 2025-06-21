import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato Sicoob no formato fornecido.
    Extrai todas as informações necessárias e retorna os dados no formato final.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Identificar início e fim das transações
    start_index = 0
    for i, line in enumerate(lines):
        if "DATA DOCUMENTO HISTÓRICO VALOR" in line:
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
    date_pattern = r"^(\d{2}/\d{2}/\d{4})\s*$"
    value_pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})([CD])"
    doc_pattern = r"^\d+$|Pix"  # Documento pode ser número ou "Pix"
    
    current_transaction = []
    current_date = None
    
    for i, line in enumerate(transaction_lines):
        # Nova data indica início de uma nova transação ou grupo de transações
        date_match = re.match(date_pattern, line)
        if date_match:
            # Processar transação anterior
            if current_transaction:
                transaction_text = "\n".join(current_transaction)
                processed = _process_single_transaction(transaction_text, date_pattern, value_pattern, doc_pattern)
                if processed:
                    data.append(processed)
                current_transaction = []
            
            current_date = date_match.group(1)
            current_transaction.append(line)
        elif current_date:
            current_transaction.append(line)
            
            # Verificar se é "SALDO DO DIA" para finalizar a transação atual
            if "SALDO DO DIA" in line:
                if current_transaction:
                    transaction_text = "\n".join(current_transaction)
                    processed = _process_single_transaction(transaction_text, date_pattern, value_pattern, doc_pattern)
                    if processed:
                        data.append(processed)
                current_transaction = []
                current_date = None
                continue  # Pular para a próxima linha (ignorando a linha de saldo)
    
    # Processar última transação, se houver
    if current_transaction and current_date:
        transaction_text = "\n".join(current_transaction)
        processed = _process_single_transaction(transaction_text, date_pattern, value_pattern, doc_pattern)
        if processed:
            data.append(processed)
    
    return data

def _process_single_transaction(transaction, date_pattern, value_pattern, doc_pattern):
    """Função auxiliar para processar uma única transação"""
    lines = transaction.split("\n")
    
    # Ignorar transações que são apenas saldos
    if any(s in transaction for s in ["SALDO ANTERIOR", "SALDO BLOQUEADO"]):
        return None
    
    # Remover "SALDO DO DIA ===== >" e a linha seguinte, se presentes
    cleaned_lines = []
    skip_next = False
    for line in lines:
        if "SALDO DO DIA" in line:
            skip_next = True
            continue
        if skip_next:
            skip_next = False
            continue
        cleaned_lines.append(line)
    
    if not cleaned_lines:
        return None
    
    # Extrair data
    date_match = re.match(date_pattern, cleaned_lines[0])
    if not date_match:
        return None
    date = date_match.group(1)
    
    # Extrair valor e tipo
    value = None
    transaction_type = None
    value_line_index = None
    
    for i, line in enumerate(cleaned_lines[1:], start=1):
        value_match = re.match(value_pattern, line.strip())
        if value_match:
            value = value_match.group(1)
            transaction_type = value_match.group(2)
            value_line_index = i
            break
    
    if not value or not transaction_type:
        return None
    
    # Remover ",00" do valor, se aplicável
    if value.endswith(",00"):
        value = value[:-3]
    
    # Extrair documento e descrição
    description_lines = []
    doc_number = None
    for i, line in enumerate(cleaned_lines[1:], start=1):
        if i == value_line_index:
            continue
        if re.match(date_pattern, line):
            break
        if not doc_number and re.match(doc_pattern, line.strip()):
            doc_number = line.strip()
            continue
        description_lines.append(line.strip())  # Incluir todas as linhas restantes como descrição
    
    description = " ".join(description_lines).strip()
    
    # Se não houver descrição, usar o documento como descrição
    if not description and doc_number:
        description = doc_number
    
    # Se ainda não houver descrição, a transação pode ser válida
    if not description:
        description = "Transação sem descrição"
    
    # Incluir número do documento na descrição, se existir
    if doc_number and doc_number != "Pix":
        description = f"{doc_number} {description}"
    
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