"""
Leitor de Notas de Locação → linha de importação
Identifica o modelo pelo CNPJ do emitente e gera a linha no novo formato.
"""

import re
import os
from datetime import datetime


# ── Mapeamento CNPJ → código carregado do CSV base ───────────────────────────

def _load_cnpj_codes() -> dict:
    """Lê base_cnpj_limpa.csv e retorna {cnpj_digits: codigo_str}."""
    base = os.path.join(os.path.dirname(__file__), '..', 'base_cnpj_limpa.csv')
    base = os.path.normpath(base)
    mapping = {}
    if not os.path.exists(base):
        return mapping
    with open(base, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            parts = line.strip().split(';')
            if len(parts) < 2:
                continue
            codigo, cnpj = parts[0].strip(), parts[1].strip()
            digits = re.sub(r'\D', '', cnpj)
            if digits and codigo and codigo.isdigit():
                mapping[digits] = codigo
    return mapping

CNPJ_TO_CODE: dict = _load_cnpj_codes()


# ── Modelos (emitentes conhecidos) ────────────────────────────────────────────

MODELS = {
    "31889563000106": {
        "name": "LOGIN TRANSPORTES E LOCAÇÕES LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "1",
        "cst_pis": "49",
        "parser": "login_transportes",
    },
    "44132928000103": {
        "name": "COPIADORA 2 DINHO LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "1",
        "cst_pis": "49",
        "parser": "copiadora_dinho",
    },
    "02904254000160": {
        "name": "LIBERINO LOPES VALENTE JUNIOR",
        "tipo_documento": 6,
        "indicador_operacao": "1",
        "cst_pis": "49",
        "parser": "copiadora_dinho",
    },
    "45762015000125": {
        "name": "GLOBAL SOLUTIONS COM E SERV LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "1",
        "cst_pis": "49",
        "parser": "global_solutions",
    },
    "22155582000118": {
        "name": "LESSA TRANSPORTE E LOCAÇÃO DE EQUIPAMENTOS",
        "tipo_documento": 6,
        "indicador_operacao": "1",
        "cst_pis": "49",
        "parser": "copiadora_dinho",
    },
    "11371839000152": {
        "name": "SEMD ENGENHARIA LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "1",
        "cst_pis": "01",
        "parser": "global_solutions",
    },
}


ESTADOS_BR = {
    'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
    'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_cnpj(text):
    return re.sub(r"\D", "", text)


def _parse_date_br(text):
    text = text.strip()
    try:
        return datetime.strptime(text, "%d/%m/%Y").strftime("%Y%m%d")
    except ValueError:
        return text


def _parse_value_br(text):
    text = re.sub(r"R\$\s*", "", text).strip()
    text = text.replace("(", "-").replace(")", "")
    text = re.sub(r"\s", "", text)
    text = text.replace(".", "").replace(",", ".")
    return float(text)


# ── Identificação do emitente ─────────────────────────────────────────────────

_CNPJ_FLEX = r"\d{2}\.?\d{3}\.?\d{3}[/\-]\d{4}[/\-]\d{2}"

def _find_model_cnpj(content):
    for raw in re.findall(_CNPJ_FLEX, content):
        cleaned = _clean_cnpj(raw)
        if cleaned in MODELS:
            return cleaned, MODELS[cleaned]

    return None, None


# ── Extração do destinatário ──────────────────────────────────────────────────

_CPF_FLEX = r"\d{3}\.?\d{3}\.?\d{3}[/\-]?\d{2}"

def _extract_dest_cnpj(content, emitente_cnpj):
    """
    Retorna o documento fiscal do destinatário em dígitos (CNPJ ou CPF).
    Tenta primeiro achar um segundo CNPJ; se não achar, busca CPF.
    """
    cnpj_pattern = r"\d{2}\.?\d{3}\.?\d{3}[/\-]\d{4}[/\-]\d{2}"
    cnpjs = [_clean_cnpj(c) for c in re.findall(cnpj_pattern, content)]
    for c in cnpjs:
        if c != emitente_cnpj:
            return c

    # Fallback: busca CPF (11 dígitos) removendo CNPJs para evitar falso positivo
    content_sem_cnpj = re.sub(cnpj_pattern, '', content)
    cpfs = re.findall(_CPF_FLEX, content_sem_cnpj)
    if cpfs:
        return _clean_cnpj(cpfs[0])

    return ""


def _extract_uf(content):
    """Extrai a UF do destinatário (ex: 'RJ') procurando após CEP ou label UF."""
    # Tenta pegar UF na linha do CEP: '28200-000 SÃO JOAO DA BARRA RJ ...'
    m = re.search(r"\d{5}-?\d{3}\s+[\w\s]+\s+([A-Z]{2})\b", content)
    if m and m.group(1) in ESTADOS_BR:
        return m.group(1)
    # Fallback: busca UF como label seguida de 2 letras
    m = re.search(r"\bUF\b[^\n]*?([A-Z]{2})\b", content)
    if m and m.group(1) in ESTADOS_BR:
        return m.group(1)
    return ""


# ── Parsers específicos ───────────────────────────────────────────────────────

def _parser_login_transportes(content):
    data = {}
    m = re.search(r"N[ÚU]MERO\s+(\d+)", content, re.IGNORECASE)
    if m:
        data["numero_documento"] = int(m.group(1))
    m = re.search(r"DATA EMISS[ÃA]O\s+(\d{2}/\d{2}/\d{4})", content)
    if m:
        data["data_operacao"] = _parse_date_br(m.group(1))
    m = re.search(r"PRAZO DE PAGAMENTO\s+(\d{2}/\d{2}/\d{4})", content)
    data["condicao_pagamento"] = "P" if m else "V"
    m = re.search(r"TOTAL DA LOCA[ÇC][ÃA]O\s+R\$\s*([\d.,]+)", content)
    if m:
        data["valor_operacao"] = _parse_value_br(m.group(1))
    return data


def _parser_copiadora_dinho(content):
    data = {}
    m = re.search(r"N[º°ú][:.]?\s*(\d+)", content)
    if m:
        data["numero_documento"] = int(m.group(1))
    m = re.search(r"Emiss[ãa]o:\s*(\d{2}/\d{2}/\d{4})", content)
    if m:
        data["data_operacao"] = _parse_date_br(m.group(1))
    data["condicao_pagamento"] = "P"
    valores = re.findall(r"R\$\s*([\d .]+,\d{2})", content)
    if valores:
        data["valor_operacao"] = _parse_value_br(valores[-1])
    return data


def _parser_global_solutions(content):
    data = {}
    m = re.search(r"Fatura\s+n\s*[º°]?\s*[:\-]?\s*(\d+)", content, re.IGNORECASE)
    if m:
        data["numero_documento"] = int(m.group(1))
    m = re.search(r"Data\s+da\s+fatura:\s*(\d{2}/\d{2}/\d{4})", content, re.IGNORECASE)
    if m:
        data["data_operacao"] = _parse_date_br(m.group(1))
    data["condicao_pagamento"] = "P" if re.search(r"vencimento", content, re.IGNORECASE) else "V"
    m = re.search(r"Total\s+R\$\s*([\d .]+,\d{2})", content, re.IGNORECASE)
    if m:
        data["valor_operacao"] = _parse_value_br(m.group(1))
    return data


PARSERS = {
    "login_transportes": _parser_login_transportes,
    "copiadora_dinho":   _parser_copiadora_dinho,
    "global_solutions":  _parser_global_solutions,
}


# ── Geração da linha ──────────────────────────────────────────────────────────

def _generate_line(model, invoice_data, dest_field, uf_dest):
    cst   = model["cst_pis"]
    valor = invoice_data.get("valor_operacao", 0.0)
    v     = f"{valor:.2f}"
    q     = lambda s: f'"{s}"'
    e     = '""'
    b     = ''       # bare empty (sem aspas)

    fields = [
        str(model["tipo_documento"]),                       # f01: 6
        q(model["indicador_operacao"]),                     # f02: "1"
        q(dest_field),                                      # f03: CNPJ dest. ou código
        e,                                                  # f04
        q(invoice_data.get("data_operacao", "")),           # f05: data YYYYMMDD
        str(invoice_data.get("numero_documento", "")),      # f06: número nota
        q(invoice_data.get("condicao_pagamento", "P")),     # f07: "P"
        v,                                                  # f08: valor
        e,                                                  # f09
        e,                                                  # f10
        q(cst),                                             # f11: CST PIS  "49"
        cst,                                                # f12: CST PIS   49
        '0',                                                # f13
        '0',                                                # f14
        q(cst),                                             # f15: CST COFINS "49"
        v,                                                  # f16: base COFINS
        '0',                                                # f17
        '0',                                                # f18
        e,                                                  # f19
        '1',                                                # f20
        e,                                                  # f21
        '" "',                                              # f22: espaço
        b, b, b, b, b, b, b, b,                            # f23-f30: 8 vazios
        e,                                                  # f31
        q(uf_dest) if uf_dest else e,                       # f32: UF
        e, e, e,                                            # f33-f35
        b, b, b, b,                                         # f36-f39: 4 vazios
        '0.00', '0.00', '0.00', '0.00',                    # f40-f43
        b, b, b, b, b, b, b, b,                            # f44-f51: 8 vazios
        e, e,                                               # f52-f53
        b,                                                  # f54
        e,                                                  # f55
        b, b, b, b, b, b, b, b, b,                         # f56-f64: 9 vazios
        b, b, b, b, b, b, b, b, b, b,                      # f65-f74: 10 vazios
        e,                                                  # f75
        b, b, b, b, b, b, b, b, b,                         # f76-f84: 9 vazios
    ]
    return ",".join(fields)


# ── Entry point ───────────────────────────────────────────────────────────────

def processar_nota(content: str) -> dict:
    emitente_cnpj, model = _find_model_cnpj(content)
    if not model:
        cnpjs = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", content)
        return {
            "success": False,
            "linha_f100": None,
            "nome_emitente": None,
            "error": f"CNPJ não reconhecido. Detectados: {cnpjs or 'nenhum'}",
        }

    parser_fn = PARSERS.get(model["parser"])
    if not parser_fn:
        return {
            "success": False,
            "linha_f100": None,
            "nome_emitente": model["name"],
            "error": f"Parser '{model['parser']}' não implementado.",
        }

    invoice_data = parser_fn(content)
    dest_field   = _extract_dest_cnpj(content, emitente_cnpj)
    uf_dest      = _extract_uf(content)
    linha        = _generate_line(model, invoice_data, dest_field, uf_dest)

    return {
        "success": True,
        "linha_f100": linha,
        "nome_emitente": model["name"],
        "error": None,
    }
