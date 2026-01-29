import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato InfinitePay (Cloudwalk) para extrair transações.
    Suporta dois formatos de data: DD/MM/YYYY e DD Mon, YYYY
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    transactions = []
    current_date = None
    pending_transaction = None
    
    HEADER_TEXT = "Data Hora Tipo de transação Nome Detalhe Valor (R$)"
    SALDO_PATTERN = re.compile(r'^Saldo do dia\s+(?:R\$\s+)?[+-]?[\d,.]+$')
    FOOTER_START_PATTERN = re.compile(r'^A Central de Ajuda está disponível.*')
    
    MONTH_MAP = {
        'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04',
        'Mai': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
        'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'
    }
    
    VALUE_REGEX = r'([+-]\d{1,3}(?:\.\d{3})*(?:,\d{2}))$'
    
    DATE_TRANSACTION_PATTERN = re.compile(
        r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s+(.*)\s+' + VALUE_REGEX
    )
    
    DATE_MONTH_TRANSACTION_PATTERN = re.compile(
        r'^(\d{2})\s+([A-Z][a-z]{2}),?\s+(\d{4})\s+(\d{2}:\d{2})\s+(.*)\s+' + VALUE_REGEX
    )
    
    TIME_TRANSACTION_PATTERN = re.compile(
        r'^(\d{2}:\d{2})\s+(.*)\s+' + VALUE_REGEX
    )
    
    def normalize_date(day, month, year):
        month_num = MONTH_MAP.get(month, month)
        return f"{day}/{month_num}/{year}"
    
    def is_transaction_line(line):
        return (DATE_TRANSACTION_PATTERN.match(line) or 
                DATE_MONTH_TRANSACTION_PATTERN.match(line) or 
                TIME_TRANSACTION_PATTERN.match(line))
    
    start_index = 0
    try:
        start_index = lines.index(HEADER_TEXT) + 1
    except ValueError:
        pass
        
    lines = lines[start_index:]
    
    skip_footer_lines = 0
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if skip_footer_lines > 0:
            skip_footer_lines -= 1
            i += 1
            continue
        
        if FOOTER_START_PATTERN.match(line):
            skip_footer_lines = 4
            i += 1
            continue
        
        if line == HEADER_TEXT:
            i += 1
            continue

        if SALDO_PATTERN.match(line):
            current_date = None
            pending_transaction = None
            i += 1
            continue
        
        if pending_transaction:
            next_line = line
            if not is_transaction_line(next_line) and not SALDO_PATTERN.match(next_line):
                pending_transaction["Descrição"] += f" {next_line}"
                i += 1
            transactions.append(pending_transaction)
            pending_transaction = None
            continue
        
        match_date_month = DATE_MONTH_TRANSACTION_PATTERN.match(line)
        if match_date_month:
            day = match_date_month.group(1)
            month = match_date_month.group(2)
            year = match_date_month.group(3)
            current_date = normalize_date(day, month, year)
            
            hora = match_date_month.group(4)
            descricao = match_date_month.group(5).strip()
            valor_assinado = match_date_month.group(6)
            
            valor = valor_assinado[1:]
            tipo = 'C' if valor_assinado.startswith('+') else 'D'
            
            transaction = {
                "Data": current_date,
                "Descrição": f"{hora} {descricao}".strip(),
                "Valor": valor,
                "Tipo": tipo
            }
            
            if descricao.endswith("Pagamento efetuado"):
                pending_transaction = transaction
            else:
                transactions.append(transaction)
            i += 1
            continue
            
        match_date_trans = DATE_TRANSACTION_PATTERN.match(line)
        if match_date_trans:
            current_date = match_date_trans.group(1)
            hora = match_date_trans.group(2)
            descricao = match_date_trans.group(3).strip()
            valor_assinado = match_date_trans.group(4)
            
            valor = valor_assinado[1:]
            tipo = 'C' if valor_assinado.startswith('+') else 'D'
            
            transaction = {
                "Data": current_date,
                "Descrição": f"{hora} {descricao}".strip(),
                "Valor": valor,
                "Tipo": tipo
            }
            
            if descricao.endswith("Pagamento efetuado"):
                pending_transaction = transaction
            else:
                transactions.append(transaction)
            i += 1
            continue

        match_time_trans = TIME_TRANSACTION_PATTERN.match(line)
        if match_time_trans and current_date:
            hora = match_time_trans.group(1)
            descricao = match_time_trans.group(2).strip()
            valor_assinado = match_time_trans.group(3)
            
            valor = valor_assinado[1:]
            tipo = 'C' if valor_assinado.startswith('+') else 'D'
            
            transaction = {
                "Data": current_date,
                "Descrição": f"{hora} {descricao}".strip(),
                "Valor": valor,
                "Tipo": tipo
            }
            
            if descricao.endswith("Pagamento efetuado"):
                pending_transaction = transaction
            else:
                transactions.append(transaction)
            i += 1
            continue
        
        i += 1

    if pending_transaction:
        transactions.append(pending_transaction)

    return transactions

def extract_transactions(transactions):
    return transactions

def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)