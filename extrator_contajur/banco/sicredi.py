import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Sicredi para extrair transações.
    O valor considerado é sempre o primeiro valor após a descrição.
    Linhas sem data são concatenadas à descrição da transação anterior.
    Transações são consideradas apenas a partir da linha 7 (índice 6).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = lines[6:]  # ignora as 6 primeiras linhas

    transactions = []
    date_pattern = r"\d{2}/\d{2}/\d{4}"
    value_pattern = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"

    for line in lines:
        if re.match(rf"^{date_pattern}", line):
            # Linha com data: nova transação
            date_match = re.match(rf"^({date_pattern})\s+", line)
            if not date_match:
                continue

            data = date_match.group(1)
            resto = line[len(data):].strip()

            valores = re.findall(value_pattern, resto)
            if not valores:
                continue

            valor_bruto = valores[0]
            tipo = "D" if valor_bruto.startswith("-") else "C"
            valor_sem_sinal = valor_bruto.lstrip("-")
            valor_formatado = re.sub(r",00$", "", valor_sem_sinal)
            descricao = re.split(value_pattern, resto, maxsplit=1)[0].strip()

            transactions.append({
                "Data": data,
                "Descrição": descricao,
                "Valor": valor_formatado,
                "Tipo": tipo
            })

        else:
            # Linha sem data: continuação da transação anterior
            if not transactions:
                continue  # nada para concatenar ainda

            # Remove possíveis valores numéricos soltos que não fazem parte da descrição
            fragmento = re.split(value_pattern, line, maxsplit=1)[0].strip()
            if fragmento:
                transactions[-1]["Descrição"] += " " + fragmento

    return transactions


def extract_transactions(transactions):
    return transactions


def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)