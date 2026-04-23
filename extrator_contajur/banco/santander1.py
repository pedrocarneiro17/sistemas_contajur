import re
from ..auxiliares.utils import process_transactions


def preprocess_text(text):
    """
    Suporta dois layouts do Santander:
      - Aplicativo Empresas:    DD/MM/YYYY  descrição  [-]valor  saldo
      - Internet Banking:       DD/MM/YYYY  descrição  [- ]R$ valor
    Um único regex trata os dois casos.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    SKIP_KEYWORDS = {
        "Aplicativo Santander", "Internet Banking Empresarial",
        "Agência:", "Conta:", "Período", "Data/Hora:", "Saldo disponível",
        "Saldo de ContaMax", "Entenda a composição", "Central de Atendimento",
        "SAC", "Ouvidoria", "Data Histórico", "Saldo do dia",
        "4004-2125", "0800",
    }

    # Ancora em: data  ...descrição...  [- ][R$ ]valor  [saldo]
    pattern = re.compile(
        r'^(\d{2}/\d{2}/\d{4})\s+'          # G1 – data
        r'(.+?)\s+'                           # G2 – descrição
        r'(-\s*)?(?:R\$\s*)?'                 # G3 – sinal e prefixo R$ opcionais
        r'(\d{1,3}(?:\.\d{3})*,\d{2})'       # G4 – valor absoluto
        r'(?:\s+[-]?\d{1,3}(?:\.\d{3})*,\d{2})?$'  # saldo opcional (formato 1)
    )

    transactions = []
    for line in lines:
        if any(kw in line for kw in SKIP_KEYWORDS):
            continue

        m = pattern.match(line)
        if not m:
            continue

        data, description, sinal, valor_abs = m.groups()

        tipo  = "D" if sinal else "C"
        valor = valor_abs.strip()
        if valor.endswith(",00"):
            valor = valor[:-3]

        transactions.append({
            "Data":      data,
            "Descrição": description.strip(),
            "Valor":     valor,
            "Tipo":      tipo,
        })

    return transactions


def extract_transactions(transactions):
    return transactions


def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)