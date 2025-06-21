import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Sicredi para extrair transações.
    O valor considerado é sempre o primeiro valor após a descrição.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    transactions = []

    # Regex para detectar linhas de transações com data no início
    date_pattern = r"\d{2}/\d{2}/\d{4}"
    value_pattern = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"

    for line in lines:
        if not re.match(rf"^{date_pattern}", line):
            continue  # pula cabeçalhos e rodapés

        # Encontra data
        date_match = re.match(rf"^({date_pattern})\s+", line)
        if not date_match:
            continue

        data = date_match.group(1)
        resto = line[len(data):].strip()

        # Encontra todos os valores numéricos (como '100.000,00', '-1.000,50' etc.)
        valores = re.findall(value_pattern, resto)

        if not valores:
            continue

        valor_bruto = valores[0]  # o primeiro é o valor da transação
        tipo = "D" if valor_bruto.startswith("-") else "C"

        # Remove o sinal para armazenar o valor
        valor_sem_sinal = valor_bruto.lstrip("-")
        
        # Remove ,00 se for inteiro (ex: 1.000,00 → 1.000)
        valor_formatado = re.sub(r",00$", "", valor_sem_sinal)

        # Remove o valor do texto para capturar a descrição
        descricao = re.split(value_pattern, resto, maxsplit=1)[0].strip()

        transactions.append({
            "Data": data,
            "Descrição": descricao,
            "Valor": valor_formatado,
            "Tipo": tipo
        })

    return transactions

def extract_transactions(transactions):
    return transactions

def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)
