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
    v = f"{valor:.2f}"
    e = '""'

    fields = [
        str(model["tipo_documento"]),                               # 01 tipo documento (I)
        q(model["indicador_operacao"]),                             # 02 indicador operação (I)
        q(emitente_cnpj),                                           # 03 CNPJ (A)
        e,                                                          # 04 produto (A) - vazio
        q(invoice_data.get("data_operacao", "")),                   # 05 data (A)
        str(invoice_data.get("numero_documento", "")),              # 06 número documento (I)
        q(invoice_data.get("condicao_pagamento", "P")),             # 07 condição pagamento (A)
        v,                                                          # 08 valor operação (N)
        e,                                                          # 09 conta débito (A) - vazio
        e,                                                          # 10 conta crédito (A) - vazio
        q(model["cst_pis"]),                                        # 11 CST PIS (A)
        v,                                                          # 12 valor base PIS (N) = valor fatura
        e,                                                          # 13 alíquota PIS (N) - vazio
        e,                                                          # 14 valor PIS operação (N) - vazio
        q(model["cst_pis"]),                                        # 15 CST Cofins (A) = mesmo CST
        v,                                                          # 16 valor base Cofins (N) = valor fatura
        e,                                                          # 17 alíquota Cofins (N) - vazio
        e,                                                          # 18 valor Cofins operação (N) - vazio
        e,                                                          # 19 natureza base cálculo (A) - vazio
        e,                                                          # 20 indicador origem crédito (I) - vazio
        e,                                                          # 21 descrição complementar (A) - vazio
        e,                                                          # 22 centro de custo (A) - vazio
        e,                                                          # 23 valor PIS retido (N) - vazio
        e,                                                          # 24 cod. recolhimento PIS retido (I) - vazio
        e,                                                          # 25 valor Cofins retido (N) - vazio
        e,                                                          # 26 cod. recolhimento Cofins retido (I) - vazio
        e,                                                          # 27 valor CSLL retido (N) - vazio
        e,                                                          # 28 cod. recolhimento CSLL retido (I) - vazio
        e,                                                          # 29 ind. natureza retenção (I) - vazio
        e,                                                          # 30 inscrição estadual (A) - vazio
        e,                                                          # 31 UF participante (A) - vazio
        e,                                                          # 32 natureza receita (A) - vazio
        e,                                                          # 33 tabela natureza receita (A) - vazio
        e,                                                          # 34 atividade CPRB (A) - vazio
        e,                                                          # 35 valor IR retido (N) - vazio
        e,                                                          # 36 cod. recolhimento IR (I) - vazio
        e,                                                          # 37 valor ISS retido (N) - vazio
        e,                                                          # 38 cod. recolhimento ISS (I) - vazio
        e,                                                          # 39 valor total bruto Factoring (N) - vazio
        e,                                                          # 40 valor IOF Factoring (N) - vazio
        e,                                                          # 41 valor tarifas Factoring (N) - vazio
        e,                                                          # 42 valor líquido Factoring (N) - vazio
        e,                                                          # 43 outras deduções INSS (N) - vazio
        e,                                                          # 44 percentual redução base INSS (N) - vazio
        e,                                                          # 45 valor materiais terceiros (N) - vazio
        e,                                                          # 46 valor subempreitadas (N) - vazio
        e,                                                          # 47 cod. recolhimento INSS (I) - vazio
        e,                                                          # 48 tipo serviço (I) - vazio
        e,                                                          # 49 valor base cálculo INSS retida (N) - vazio
        e,                                                          # 50 valor materiais próprios (N) - vazio
        e,                                                          # 51 código participante (A) - vazio
        e,                                                          # 52 número contrato aluguel (A) - vazio
        e,                                                          # 53 valor comissão (N) - vazio
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
