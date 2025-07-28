import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do PagBank, mantendo centavos separados por vírgula
    e removendo apenas ',00' para valores redondos.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    transactions = []
    date_pattern = r"\d{2}/\d{2}/\d{4}"

    for line in lines:
        if "saldo do dia" in line.lower() or "saldododia" in line.lower():
            continue

        if not re.match(rf"^{date_pattern}", line):
            continue

        date_match = re.match(rf"^({date_pattern})\s+", line)
        if not date_match:
            continue

        data = date_match.group(1)
        resto = line[len(data):].strip()

        # Padrão para capturar valores (débito ou crédito)
        valor_match = re.search(r"(-\s*)?R\$\s*([\d.,]+)", resto)
        if not valor_match:
            continue

        # Determina o tipo e pega o valor bruto
        tipo = "D" if valor_match.group(1) else "C"
        valor_bruto = valor_match.group(2)

        # Remove pontos de milhar e trata centavos
        valor_sem_milhar = valor_bruto.replace(".", "")
        
        # Remove ',00' apenas se for valor redondo (ex: 100,00 → 100)
        valor_formatado = valor_sem_milhar.replace(",00", "") if valor_sem_milhar.endswith(",00") else valor_sem_milhar

        # Descrição (garante não vazia)
        descricao = resto[:valor_match.start()].strip() or "Transação sem descrição"

        transactions.append({
            "Data": data,
            "Descrição": descricao,
            "Valor": valor_formatado,  # Exemplos: "5616" (de 5.616,00) ou "33,71" (original)
            "Tipo": tipo
        })

    return transactions

def extract_transactions(transactions):
    return transactions

def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)