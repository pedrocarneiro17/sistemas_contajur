import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    date_pattern = r"\d{2}/\d{2}/\d{4}"
    value_pattern = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"

    # Reinsere quebras de linha antes de datas coladas no meio do texto
    text = re.sub(rf"(?<!\n)(?={date_pattern})", "\n", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print(lines[:10])  # <-- adiciona aqui temporariamente
    lines = lines[6:]

    ignorar = re.compile(
        r"^(Data\s+Descri|Sicredi\s+Fone|0800\s+|SAC\s+|Ouvidoria\s+|SALDO[\s,])",
        re.IGNORECASE
    )
    lines = [l for l in lines if not ignorar.match(l)]

    transactions = []
    fragmentos_pendentes = []

    for line in lines:
        if re.match(rf"^{date_pattern}", line):
            date_match = re.match(rf"^({date_pattern})\s*", line)
            if not date_match:
                continue

            data = date_match.group(1)
            resto = line[len(data):].strip()

            valores = re.findall(value_pattern, resto)
            if not valores:
                fragmentos_pendentes = []
                continue

            valor_bruto = valores[0]
            tipo = "D" if valor_bruto.startswith("-") else "C"
            valor_sem_sinal = valor_bruto.lstrip("-")
            valor_formatado = re.sub(r",00$", "", valor_sem_sinal)

            descricao_inline = re.split(value_pattern, resto, maxsplit=1)[0].strip()

            partes = fragmentos_pendentes + ([descricao_inline] if descricao_inline else [])
            descricao = " ".join(partes).strip()
            fragmentos_pendentes = []

            transactions.append({
                "Data": data,
                "Descrição": descricao,
                "Valor": valor_formatado,
                "Tipo": tipo
            })

        else:
            fragmento = re.split(value_pattern, line, maxsplit=1)[0].strip()
            if not fragmento:
                continue

            if not transactions or transactions[-1]["Descrição"]:
                fragmentos_pendentes.append(fragmento)
            else:
                transactions[-1]["Descrição"] = fragmento

    return transactions


def extract_transactions(transactions):
    return transactions


def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)