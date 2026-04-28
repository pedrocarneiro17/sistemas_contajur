"""
Processador Caixa – formato web (extrato_pdf impresso via browser).

Estrutura de cada transação (cada campo em linha separada):
    DD/MM/YYYY
    DD/MM HH:MM
    DOCNUM (4-8 dígitos)
    DESCRIÇÃO (1+ linhas de texto)
    [PARTE / CNPJ]
    [E-CODE]
    [- ]R$\xa0VALOR
    R$\xa0SALDO C|D
"""

import re
from ..auxiliares.utils import process_transactions

# Linha só com data: DD/MM/YYYY (sem mais nada)
DATE_ONLY_RE  = re.compile(r'^(\d{2}/\d{2}/\d{4})$')
# Data efetiva isolada: DD/MM HH:MM
EFF_DATE_RE   = re.compile(r'^\d{2}/\d{2}\s+\d{2}:\d{2}$')
# Número de documento: 4-8 dígitos isolados (ex: 021440, 000033)
DOCNUM_RE     = re.compile(r'^\d{4,8}$')
# E-code / chave Pix
ECODE_RE      = re.compile(r'^E[A-Za-z0-9]{15,}$')
# Linha de valor: '- R$\xa0X,XX' (débito) ou 'R$\xa0X,XX' (crédito, sem C/D no fim)
VALUE_LINE_RE = re.compile(r'^(-\s*)?R\$[\xa0 ]([\d.]+,\d{2})$')
# Linha de saldo: 'R$\xa0X,XX C' ou 'R$\xa0X,XX D'
SALDO_LINE_RE = re.compile(r'^R\$[\xa0 ][\d.]+,\d{2}\s+[CD]$')

SKIP_RE = re.compile(
    r'^(Data\b|Documento\b|Hist[oó]rico\b|Valor\b|Saldo\b|SALDO DIA|'
    r'Data\s+Efetiva|about:blank|SAC CAIXA|Ouvidoria|'
    r'0800\s+|Pessoas com defici|Al[oô] CAIXA|CNPJ:|Ag[eê]ncia:|'
    r'Saldo anterior|Extrato no per)',
    re.IGNORECASE
)


def preprocess_text(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    print("\n" + "="*60)
    print(f"[CAIXA2 DEBUG] Total de linhas: {len(lines)}")
    print("[CAIXA2 DEBUG] Primeiras 60 linhas:")
    for i, l in enumerate(lines[:60], 1):
        print(f"  {i:>3}: {repr(l)}")
    print("="*60)

    transactions  = []
    current_date  = None
    desc_parts    = []
    expect_eff    = False   # acabou de ver data, espera DD/MM HH:MM
    expect_docnum = False   # acabou de ver data efetiva, espera docnum
    in_trans      = False   # dentro de transação, acumulando descrição

    for line in lines:

        # ── Cabeçalhos / rodapés / linhas fixas ──────────────────────────
        if SKIP_RE.match(line):
            continue

        # ── Timestamp de impressão com vírgula (DD/MM/YYYY,HH:MM:SS) ─────
        if re.match(r'^\d{2}/\d{2}/\d{4},', line):
            continue

        # ── Linha de saldo (R$\xa0X,XX C|D) ──────────────────────────────
        if SALDO_LINE_RE.match(line):
            continue

        # ── E-code / chave Pix ────────────────────────────────────────────
        if ECODE_RE.match(line):
            continue

        # ── Fragmento de CNPJ (1-3 dígitos) quando NÃO esperamos docnum ──
        if re.match(r'^\d{1,3}$', line) and not expect_docnum:
            continue

        # ── Linha só com data (DD/MM/YYYY) ───────────────────────────────
        m = DATE_ONLY_RE.match(line)
        if m:
            current_date  = m.group(1)
            expect_eff    = True
            expect_docnum = False
            in_trans      = False
            desc_parts    = []
            continue

        # ── Data efetiva (DD/MM HH:MM) ────────────────────────────────────
        if EFF_DATE_RE.match(line):
            if expect_eff:
                expect_eff    = False
                expect_docnum = True
            continue

        # ── Número de documento ───────────────────────────────────────────
        if DOCNUM_RE.match(line) and expect_docnum:
            expect_docnum = False
            in_trans      = True
            desc_parts    = []
            continue

        # ── Linha de valor ────────────────────────────────────────────────
        mv = VALUE_LINE_RE.match(line)
        if mv and in_trans and current_date:
            is_debit = mv.group(1) is not None
            valor    = mv.group(2)
            if valor.endswith(',00'):
                valor = valor[:-3].replace('.', '')
            tipo     = 'D' if is_debit else 'C'
            desc     = ' '.join(desc_parts).strip()
            transactions.append({
                'Data':      current_date,
                'Descrição': desc,
                'Valor':     valor,
                'Tipo':      tipo,
            })
            in_trans   = False
            desc_parts = []
            continue

        # ── Acumula descrição (dentro de transação) ───────────────────────
        if in_trans and len(line) > 1:
            desc_parts.append(line)

    print(f"[CAIXA2 DEBUG] Transações encontradas: {len(transactions)}")
    return transactions


def extract_transactions(transactions):
    return transactions


def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)
