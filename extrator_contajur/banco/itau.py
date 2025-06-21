import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do Itaú para dividir transações, ignorando cabeçalho e rodapé.
    Extrai o ano do período informado e adiciona às datas das transações no formato DD/MM/YYYY.
    Contém a função auxiliar convert_date_format internamente.
    """
    def convert_date_format(date_str):
        """
        Converte datas no formato DD/mes para DD/MM.
        Ex.: 01/abr -> 01/04, 31/mar -> 31/03
        """
        month_map = {
            "jan": "01", "fev": "02", "mar": "03", "abr": "04", "mai": "05", "jun": "06",
            "jul": "07", "ago": "08", "set": "09", "out": "10", "nov": "11", "dez": "12"
        }
        match = re.match(r"(\d{2})/(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)", date_str, re.IGNORECASE)
        if match:
            day = match.group(1)
            month = month_map[match.group(2).lower()]
            return f"{day}/{month}"
        return date_str

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Extrair o ano do período (ex.: "lançamentos período: 01/04/2025 até 30/04/2025")
    year = None
    for line in lines:
        period_match = re.search(r"lançamentos período: \d{2}/\d{2}/(\d{4}) até \d{2}/\d{2}/\d{4}", line)
        if period_match:
            year = period_match.group(1)
            break
    
    # Se não encontrar o ano, usar um valor padrão (ex.: 2025)
    if not year:
        year = "2025"  # Fallback, mas idealmente deveria ser tratado como erro ou configurável

    # Identificar o início e o fim das transações
    start_index = 0
    for i, line in enumerate(lines):
        if "SALDO ANTERIOR" in line:
            start_index = i + 1
            break
    
    end_index = len(lines)
    for i, line in enumerate(lines[start_index:], start=start_index):
        if "saldo da conta corrente" in line.lower():
            end_index = i
            break
    
    transaction_lines = lines[start_index:end_index]
    
    date_pattern = r"^\d{2}\s*/\s*(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s"
    value_pattern = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"
    
    transactions = []
    
    for line in transaction_lines:
        if "SALDO TOTAL DISPON" in line:
            continue
            
        if re.match(date_pattern, line, re.IGNORECASE):
            date_match = re.match(r"(\d{2}\s*/\s*(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez))", line, re.IGNORECASE)
            value_matches = list(re.finditer(value_pattern, line))
            
            if date_match and value_matches:
                date = date_match.group(1).replace(" ", "")
                date = convert_date_format(date)
                # Adicionar o ano ao formato DD/MM/YYYY
                date_with_year = f"{date}/{year}"
                value = value_matches[0].group()
                desc_start = date_match.end()
                desc_end = value_matches[0].start()
                description = line[desc_start:desc_end].strip()
                
                tipo = "D" if value.startswith("-") else "C"
                valor = value.replace("-", "")
                
                # Ajustar valor: remover ",00" se for um número inteiro
                if valor.endswith(",00"):
                    valor = valor[:-3]
                
                transactions.append({
                    "Data": date_with_year,
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
    Processa o texto extraído do Itaú e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)