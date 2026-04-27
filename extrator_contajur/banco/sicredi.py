import re
from ..auxiliares.utils import process_transactions

DATE_RE  = re.compile(r'^\d{2}/\d{2}/\d{4}')
VALUE_RE = re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}')
ALL_VALUES_RE = re.compile(r'-?\d{1,3}(?:\.\d{3})*,\d{2}')

SKIP_RE = re.compile(
    r'^(Data\b|Descrição|Documento|Valor\s*\(R\$\)|Saldo\s*\(R\$\)|SALDO'
    r'|Cooperativa:|Conta Corrente:|Associado:|Impresso em|^Extrato$|Dados referentes'
    r'|Sicredi\s+Fone|0800\s+|SAC\s+|Ouvidoria)',
    re.IGNORECASE
)


def preprocess_text(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    transactions = []
    current    = None
    skip_saldo = False   # próxima linha numérica é o saldo → ignorar

    for line in lines:

        # ── Aguardando saldo (linha após o valor) ─────────────────────────────
        if skip_saldo:
            skip_saldo = False
            if VALUE_RE.match(line):
                continue   # era o saldo, descarta
            # Não era valor (ex.: cabeçalho repetido) → processa normalmente

        # ── Cabeçalhos e rodapés ──────────────────────────────────────────────
        if SKIP_RE.match(line):
            continue

        # ── Nova transação ─────────────────────────────────────────────────────
        if DATE_RE.match(line):
            current = {
                "Data":      line[:10],
                "Descrição": line[10:].strip(),
                "Valor":     None,
                "Tipo":      None,
            }
            continue

        if current is None:
            continue

        # ── Linha de valor ─────────────────────────────────────────────────────
        if VALUE_RE.match(line):
            all_vals = ALL_VALUES_RE.findall(line)
            val  = all_vals[0]
            tipo = "D" if val.startswith("-") else "C"
            current["Valor"] = val.lstrip("-")
            current["Tipo"]  = tipo
            transactions.append(current)
            current = None

            if len(all_vals) >= 2:
                # Valor e saldo na mesma linha (ex.: "-167.533,61 5.942.613,47")
                skip_saldo = False
            else:
                skip_saldo = True  # próxima linha numérica é o saldo
            continue

        # ── Descrição / número de documento ───────────────────────────────────
        if current["Descrição"]:
            current["Descrição"] += " " + line
        else:
            current["Descrição"] = line

    if current and current["Valor"] is not None:
        transactions.append(current)

    return transactions


def extract_transactions(transactions):
    return transactions


def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)
