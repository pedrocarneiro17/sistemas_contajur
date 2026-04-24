"""
Leitor de Notas de Locação → F100 EFD PIS/COFINS
Identifica o modelo pelo CNPJ do emitente e gera linha no formato F100.
"""

import re
from datetime import datetime


MODELS = {
    "31889563000106": {
        "name": "LOGIN TRANSPORTES E LOCAÇÕES LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "2",
        "produto": "Locação de Bens Móveis",
        "cst_pis": "49",
        "parser": "login_transportes",
    },
    "44132928000103": {
        "name": "COPIADORA 2 DINHO LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "2",
        "cst_pis": "49",
        "parser": "copiadora_dinho",
    },
    "45762015000125": {
        "name": "GLOBAL SOLUTIONS COM E SERV LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "2",
        "cst_pis": "49",
        "parser": "global_solutions",
    },
    "22155582000118": {
        "name": "LESSA TRANSPORTE E LOCAÇÃO DE EQUIPAMENTOS",
        "tipo_documento": 6,
        "indicador_operacao": "2",
        "cst_pis": "49",
        "parser": "copiadora_dinho",
    },
    "11371839000152": {
        "name": "SEMD ENGENHARIA LTDA",
        "tipo_documento": 6,
        "indicador_operacao": "2",
        "cst_pis": "01",
        "parser": "global_solutions",
    },
}


def _clean_cnpj(text):
    return re.sub(r"\D", "", text)


def _parse_date_br(text):
    text = text.strip()
    try:
        return datetime.strptime(text, "%d/%m/%Y").strftime("%d%m%Y")
    except ValueError:
        return text


def _parse_value_br(text):
    text = re.sub(r"R\$\s*", "", text).strip()
    text = text.replace("(", "-").replace(")", "")
    text = re.sub(r"\s", "", text)
    text = text.replace(".", "").replace(",", ".")
    return float(text)


def _find_model_cnpj(content):
    for raw in re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", content):
        cleaned = _clean_cnpj(raw)
        if cleaned in MODELS:
            return cleaned, MODELS[cleaned]

    for m in re.finditer(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-)", content):
        trecho = content[m.end():m.end() + 80]
        d = re.search(r"(\d{2})", trecho)
        if d:
            raw = m.group(1) + d.group(1)
            cleaned = _clean_cnpj(raw)
            if cleaned in MODELS:
                return cleaned, MODELS[cleaned]

    return None, None


def _parser_login_transportes(content):
    data = {}
    m = re.search(r"NÚMERO\s+(\d+)", content)
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
    "copiadora_dinho": _parser_copiadora_dinho,
    "global_solutions": _parser_global_solutions,
}


def _generate_f100_line(model, invoice_data, emitente_cnpj):
    def q(v):
        return f'"{v}"'

    valor = invoice_data.get("valor_operacao", 0.0)
    fields = [
        str(model["tipo_documento"]),
        q(model["indicador_operacao"]),
        q(emitente_cnpj),
        q(invoice_data.get("data_operacao", "")),
        f"{valor:.2f}",
        q(invoice_data.get("condicao_pagamento", "P")),
        str(invoice_data.get("numero_documento", "")),
        q(model["cst_pis"]),
    ]
    return ",".join(fields)


def processar_nota(content: str) -> dict:
    """
    Recebe o texto extraído de uma nota de locação e retorna:
    {
        "success": bool,
        "linha_f100": str,
        "nome_emitente": str,
        "error": str | None
    }
    """
    emitente_cnpj, model = _find_model_cnpj(content)
    if not model:
        cnpjs_detectados = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", content)
        return {
            "success": False,
            "linha_f100": None,
            "nome_emitente": None,
            "error": f"CNPJ não reconhecido. CNPJs detectados: {cnpjs_detectados or 'nenhum'}",
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
    linha = _generate_f100_line(model, invoice_data, emitente_cnpj)

    return {
        "success": True,
        "linha_f100": linha,
        "nome_emitente": model["name"],
        "error": None,
    }
