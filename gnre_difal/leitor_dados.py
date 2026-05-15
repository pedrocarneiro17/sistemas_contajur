"""
Leitura e validação dos dados de entrada (Excel ou CSV).

Colunas obrigatórias:
  uf_favorecida        - UF destinatária (ex: SP)
  cnpj_emitente        - CNPJ da empresa (somente números ou formatado)
  razao_social         - Razão social da empresa emitente
  uf_emitente          - UF da empresa emitente (ex: SP)
  municipio_emitente   - Código IBGE 5 dígitos da cidade emitente
  periodo_referencia   - Competência AAAAMM (ex: 202501)
  valor_principal      - Valor ICMS DIFAL (decimal)
  data_vencimento      - Data de vencimento AAAA-MM-DD

Colunas opcionais:
  tipo_gnre            - 0=Simples (padrão), 1=Múlt.docs, 2=Múlt.receitas
  cpf_emitente / ie_emitente
  endereco             - Endereço do emitente
  cep / telefone
  receita              - Código 6 dígitos (vazio = 100080 padrão DIFAL)
  valor_fecp           - Valor FECP/FCP (se houver)
  cnpj_destinatario / cpf_destinatario / ie_destinatario
  razao_social_destinatario
  municipio_destinatario
  documento_origem_tipo / documento_origem
  data_pagamento       - AAAA-MM-DD
  identificador_guia   - até 10 dígitos
"""

import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from gnre_difal.models import DifAlGuia

logger = logging.getLogger(__name__)

UFS_VALIDAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

COLUNAS_OBRIGATORIAS = {
    "uf_favorecida", "cnpj_emitente", "razao_social",
    "uf_emitente", "municipio_emitente",
    "periodo_referencia", "valor_principal", "data_vencimento",
}


def _str(row, col, default="") -> str:
    v = row.get(col, default)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    return str(v).strip()


def _dec(row, col) -> Decimal:
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return Decimal("0.00")
    try:
        return Decimal(str(v).replace(",", ".").strip())
    except InvalidOperation:
        return Decimal("0.00")


def _cnpj(row, col) -> str:
    """Extrai só dígitos. Recupera zero à esquerda: 13 dígitos → zfill(14), 10 → zfill(11)."""
    digitos = "".join(c for c in _str(row, col) if c.isdigit())
    if len(digitos) == 13:          # CNPJ perdeu o zero inicial
        digitos = digitos.zfill(14)
    elif len(digitos) == 10:        # CPF perdeu o zero inicial
        digitos = digitos.zfill(11)
    return digitos


def _ie(row, col) -> str:
    """
    IE deve ter entre 2 e 16 dígitos numéricos (padrão TIe do schema GNRE).
    Extrai apenas dígitos e descarta se fora do intervalo.
    """
    digitos = "".join(c for c in _str(row, col) if c.isdigit())
    if not digitos:
        return ""
    if 2 <= len(digitos) <= 16:
        return digitos
    return ""   # fora do padrão — omite para não gerar erro no portal


def _data(row, col) -> str:
    """
    Retorna data no formato AAAA-MM-DD.
    Aceita:
      - Strings 'AAAA-MM-DD', 'DD/MM/AAAA', 'AAAAMM' (período), Timestamp do pandas, etc.
    """
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    # pandas Timestamp ou datetime → iso só com data
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    # Remove eventual horário '2025-01-15 00:00:00' → '2025-01-15'
    if " " in s:
        s = s.split(" ")[0]
    # DD/MM/AAAA → AAAA-MM-DD
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        d, m, a = s.split("/")
        return f"{a}-{m}-{d}"
    return s


_TIPOS_DOC_VALIDOS = {"10", "55", "57", "65", "66", "67"}

# Mapa de descrições comuns → código numérico (para tolerar erros de preenchimento)
_TIPOS_DOC_ALIAS = {
    "nfe": "55", "nf-e": "55", "nota fiscal eletronica": "55",
    "nota fiscal eletrônica": "55", "chave da nfe": "55", "chave nfe": "55",
    "cte": "57", "ct-e": "57",
    "nfce": "65", "nfc-e": "65",
    "nf": "10", "nota fiscal": "10",
}


def _doc_tipo(row) -> str:
    """
    Retorna o código de 2 dígitos para o tipo do documento de origem.
    Aceita o código numérico direto ('55') ou descrições como 'NF-e', 'Chave da NFe'.
    Retorna '' se inválido (elemento <documentoOrigem> será omitido).
    """
    v = _str(row, "documento_origem_tipo")
    if not v:
        return ""
    # Já é código numérico de 2 dígitos?
    if v.isdigit() and len(v) == 2:
        return v
    # Tenta mapear por alias (case-insensitive)
    alias = _TIPOS_DOC_ALIAS.get(v.lower().strip())
    if alias:
        logger.warning(
            "documento_origem_tipo '%s' convertido para código '%s'.", v, alias
        )
        return alias
    logger.warning(
        "documento_origem_tipo '%s' inválido (esperado 2 dígitos numéricos, ex: 55). "
        "Campo <documentoOrigem> será omitido.",
        v,
    )
    return ""


def _id_guia(row) -> str:
    """identificadorGuia: 1–10 dígitos numéricos. Qualquer texto é descartado."""
    digitos = "".join(c for c in _str(row, "identificador_guia") if c.isdigit())
    return digitos[:10] if digitos else ""


def _detalhe(row, linha: int) -> str:
    """
    Retorna o detalhamento_receita como digitado na planilha (somente dígitos).
    O valor é passado diretamente ao XML sem zero-padding.
    """
    v = _str(row, "detalhamento_receita")
    if not v:
        return ""
    digitos = "".join(c for c in v if c.isdigit())
    if not digitos:
        logger.warning("Linha %d: detalhamento_receita '%s' não contém dígitos — campo omitido.", linha, v)
        return ""
    return digitos


def ler_planilha(caminho: str | Path) -> list[DifAlGuia]:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    if caminho.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        # Colunas com zeros à esquerda devem ser lidas como texto.
        # As de data ficam sem dtype para preservar Timestamp do Excel.
        _str_cols = {
            "cnpj_emitente", "cpf_emitente", "ie_emitente",
            "cnpj_destinatario", "cpf_destinatario", "ie_destinatario",
            "municipio_emitente", "municipio_destinatario",
            "cep", "telefone", "periodo_referencia",
            "receita", "detalhamento_receita", "identificador_guia", "documento_origem", "chave_acesso",
            "uf_favorecida", "uf_emitente", "razao_social",
            "razao_social_destinatario", "endereco",
            "tipo_gnre", "documento_origem_tipo",
        }
        df = pd.read_excel(caminho, dtype={c: str for c in _str_cols})
    else:
        df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    _validar_colunas(df)

    # Remove linhas de descrição do modelo (linha 2 do Excel gerado pelo sistema)
    # Detecta pela coluna uf_favorecida: se não for uma UF de 2 letras válida E
    # o valor contém texto longo, é linha de instrução — descarta silenciosamente.
    if "uf_favorecida" in df.columns:
        df = df[df["uf_favorecida"].apply(
            lambda v: str(v).strip().upper() in UFS_VALIDAS
            if pd.notna(v) and str(v).strip() != "" else False
        )].reset_index(drop=True)

    guias: list[DifAlGuia] = []
    erros = 0

    for idx, row in df.iterrows():
        linha = idx + 2
        try:
            uf_fav = _str(row, "uf_favorecida").upper()
            if uf_fav not in UFS_VALIDAS:
                logger.warning("Linha %d: uf_favorecida inválida '%s'", linha, uf_fav)
                erros += 1
                continue

            cnpj = _cnpj(row, "cnpj_emitente")
            if len(cnpj) not in (11, 14):
                logger.warning("Linha %d: cnpj_emitente inválido '%s'", linha, cnpj)
                erros += 1
                continue

            periodo = _str(row, "periodo_referencia")
            # Pandas pode ler 202501 como inteiro → '202501.0'
            if "." in periodo:
                periodo = periodo.split(".")[0]
            if len(periodo) != 6 or not periodo.isdigit():
                logger.warning("Linha %d: periodo_referencia inválido '%s'", linha, periodo)
                erros += 1
                continue

            valor = _dec(row, "valor_principal")
            if valor <= Decimal("0"):
                logger.warning("Linha %d: valor_principal inválido", linha)
                erros += 1
                continue

            guia = DifAlGuia(
                uf_favorecida=uf_fav,
                tipo_gnre=_str(row, "tipo_gnre", "0"),
                cnpj_emitente=cnpj,
                cpf_emitente=_cnpj(row, "cpf_emitente"),
                ie_emitente=_ie(row, "ie_emitente"),
                razao_social=_str(row, "razao_social"),
                endereco=_str(row, "endereco"),
                municipio_emitente=_str(row, "municipio_emitente"),
                uf_emitente=_str(row, "uf_emitente").upper(),
                cep=_cnpj(row, "cep"),
                telefone=_cnpj(row, "telefone"),
                receita=_str(row, "receita"),
                periodo_referencia=periodo,  # já normalizado acima
                data_vencimento=_data(row, "data_vencimento"),
                valor_principal=valor,
                valor_fecp=_dec(row, "valor_fecp"),
                valor_juros=_dec(row, "valor_juros"),
                valor_multa=_dec(row, "valor_multa"),
                cnpj_destinatario=_cnpj(row, "cnpj_destinatario"),
                cpf_destinatario=_cnpj(row, "cpf_destinatario"),
                ie_destinatario=_ie(row, "ie_destinatario"),
                razao_social_destinatario=_str(row, "razao_social_destinatario"),
                municipio_destinatario=_str(row, "municipio_destinatario"),
                detalhamento_receita=_detalhe(row, linha),
                documento_origem_tipo=_doc_tipo(row),
                documento_origem=_str(row, "documento_origem"),
                chave_acesso="".join(c for c in _str(row, "chave_acesso") if c.isdigit()),
                data_pagamento=_data(row, "data_pagamento"),
                identificador_guia=_id_guia(row),
            )
            guias.append(guia)

        except Exception as e:
            logger.error("Linha %d: erro: %s", linha, e)
            erros += 1

    logger.info("Leitura: %d guias válidas, %d erros", len(guias), erros)
    return guias


def _validar_colunas(df: pd.DataFrame) -> None:
    faltando = COLUNAS_OBRIGATORIAS - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas obrigatórias faltando: {sorted(faltando)}")
