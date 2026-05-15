"""
Geração dos XMLs de lote GNRE conforme estrutura TDadosGNRE v2.00.

Estrutura correta (manual GNRE):
  <TLote_GNRE versao="2.00" xmlns="http://www.gnre.pe.gov.br">
    <guias>
      <TDadosGNRE versao="2.00">
        <ufFavorecida>SP</ufFavorecida>
        <tipoGnre>0</tipoGnre>
        <contribuinteEmitente>
          <identificacao><CNPJ>...</CNPJ></identificacao>
          <razaoSocial>...</razaoSocial>
          ...
        </contribuinteEmitente>
        <itensGNRE>
          <item>
            <receita>100080</receita>
            <referencia><mes>01</mes><ano>2025</ano></referencia>
            <dataVencimento>2025-02-20</dataVencimento>
            <valor tipo="11">1500.00</valor>   <!-- principal ICMS -->
            <valor tipo="21">1500.00</valor>   <!-- total ICMS     -->
          </item>
        </itensGNRE>
        <valorGNRE>1500.00</valorGNRE>
        <dataPagamento>2025-02-20</dataPagamento>
      </TDadosGNRE>
    </guias>
  </TLote_GNRE>
"""

import logging
from decimal import Decimal
from lxml import etree

from gnre_difal.models import DifAlGuia

logger = logging.getLogger(__name__)

NS    = "http://www.gnre.pe.gov.br"
NSMAP = {None: NS}

# ---------------------------------------------------------------------------
# Mapeamento UF → comportamento da chave de acesso NF-e/CT-e
#
# "campo_extra_codigo": código exigido como campoExtra para a chave
# "omitir_doc_origem" : True = UF não aceita chave de 44 dígitos em
#                       <documentoOrigem>; a chave deve ir SÓ como campoExtra
#
# UFs não listadas aqui usam o comportamento padrão:
#   campo extra 99 + mantém <documentoOrigem> normalmente.
# ---------------------------------------------------------------------------
_UF_CHAVE_CONFIG: dict[str, dict] = {
    "MG": {"campo_extra_codigo": "83", "omitir_doc_origem": True},
    "GO": {"campo_extra_codigo": "83", "omitir_doc_origem": True},
    # Adicione outras UFs conforme o portal reportar erros:
    # "XX": {"campo_extra_codigo": "83", "omitir_doc_origem": True},
}
_CAMPO_EXTRA_CHAVE_PADRAO = "99"   # código usado por todas as UFs não listadas acima


def _sub(pai, tag: str, texto: str | None = None) -> etree._Element:
    el = etree.SubElement(pai, tag)
    if texto is not None:
        el.text = texto
    return el


def _fmt(v: Decimal) -> str:
    return f"{v:.2f}"


def _cnpj(v: str) -> str:
    return "".join(c for c in (v or "") if c.isdigit())


# ---------------------------------------------------------------------------
# Bloco contribuinteEmitente
# ---------------------------------------------------------------------------

def _bloco_emitente(pai, g: DifAlGuia) -> None:
    em = _sub(pai, "contribuinteEmitente")
    ident = _sub(em, "identificacao")

    cnpj = _cnpj(g.cnpj_emitente)
    cpf  = _cnpj(g.cpf_emitente)
    ie   = (g.ie_emitente or "").strip()

    if cnpj:
        _sub(ident, "CNPJ", cnpj)
    elif cpf:
        _sub(ident, "CPF", cpf)
    elif ie:
        _sub(ident, "IE", ie)

    # razaoSocial, endereco, municipio, uf são obrigatórios quando id = CNPJ/CPF
    if g.razao_social:
        _sub(em, "razaoSocial", g.razao_social)
    if g.endereco:
        _sub(em, "endereco", g.endereco)
    if g.municipio_emitente:
        _sub(em, "municipio", g.municipio_emitente)
    if g.uf_emitente:
        _sub(em, "uf", g.uf_emitente.upper())
    if g.cep:
        _sub(em, "cep", _cnpj(g.cep))
    if g.telefone:
        _sub(em, "telefone", _cnpj(g.telefone))


# ---------------------------------------------------------------------------
# Bloco item dentro de itensGNRE
# ---------------------------------------------------------------------------

def _bloco_item(pai, g: DifAlGuia) -> None:
    item = _sub(pai, "item")

    _sub(item, "receita", g.codigo_receita)

    if g.detalhamento_receita:
        _sub(item, "detalhamentoReceita", g.detalhamento_receita)

    # Documento de origem (NF-e, etc.)
    # Algumas UFs não aceitam a chave de 44 dígitos em <documentoOrigem> —
    # nesses casos ela vai SOMENTE como campoExtra (ver _UF_CHAVE_CONFIG).
    uf_cfg = _UF_CHAVE_CONFIG.get(g.uf_favorecida.upper(), {})
    chave_44 = "".join(c for c in (g.documento_origem or "") if c.isdigit())
    chave_eh_nfe = len(chave_44) == 44
    omitir_doc_origem = uf_cfg.get("omitir_doc_origem", False) and chave_eh_nfe

    if g.documento_origem and g.documento_origem_tipo and not omitir_doc_origem:
        doc = _sub(item, "documentoOrigem", g.documento_origem)
        doc.set("tipo", g.documento_origem_tipo)
    elif g.documento_origem and not g.documento_origem_tipo and not omitir_doc_origem:
        logger.warning(
            "UF %s: 'documento_origem' preenchido mas 'documento_origem_tipo' vazio — "
            "elemento <documentoOrigem> omitido (tipo é obrigatório pelo schema).",
            g.uf_favorecida,
        )

    # Referência (mês / ano de competência)
    if g.mes_referencia and g.ano_referencia:
        ref = _sub(item, "referencia")
        _sub(ref, "mes", g.mes_referencia)
        _sub(ref, "ano", g.ano_referencia)

    if g.data_vencimento:
        _sub(item, "dataVencimento", g.data_vencimento)

    # Valores
    if g.valor_principal > Decimal("0"):
        v11 = _sub(item, "valor", _fmt(g.valor_principal))
        v11.set("tipo", "11")                                 # principal ICMS
        v21 = _sub(item, "valor", _fmt(g.total_icms))
        v21.set("tipo", "21")                                 # total ICMS

    if g.valor_fecp > Decimal("0"):
        v12 = _sub(item, "valor", _fmt(g.valor_fecp))
        v12.set("tipo", "12")                                 # principal FECP
        v22 = _sub(item, "valor", _fmt(g.total_fecp))
        v22.set("tipo", "22")                                 # total FECP

    # Destinatário (quando exigido pela UF)
    _bloco_destinatario(item, g)

    # Campos extras (máx 3)
    # Injeta automaticamente o campo extra com a chave de acesso NF-e/CT-e
    # usando o código correto para cada UF (83, 99, etc.).
    campos_extras_efetivos = list(g.campos_extras or [])
    codigos_ja_presentes = {str(c) for c, _ in campos_extras_efetivos}
    codigo_chave = uf_cfg.get("campo_extra_codigo", _CAMPO_EXTRA_CHAVE_PADRAO)

    if chave_eh_nfe and codigo_chave not in codigos_ja_presentes:
        campos_extras_efetivos.insert(0, (codigo_chave, chave_44))
        logger.debug("UF %s: campo extra %s (chave NF-e) injetado automaticamente.",
                     g.uf_favorecida, codigo_chave)

    if campos_extras_efetivos:
        extras = _sub(item, "camposExtras")
        for cod, val in campos_extras_efetivos[:3]:
            ce = _sub(extras, "campoExtra")
            _sub(ce, "codigo", str(cod))
            _sub(ce, "valor", str(val))


# ---------------------------------------------------------------------------
# Bloco contribuinteDestinatario (opcional)
# ---------------------------------------------------------------------------

def _bloco_destinatario(pai, g: DifAlGuia) -> None:
    cnpj = _cnpj(g.cnpj_destinatario)
    cpf  = _cnpj(g.cpf_destinatario)
    ie   = (g.ie_destinatario or "").strip()

    if not (cnpj or cpf or ie):
        return  # não inclui o bloco se não há dados

    dest = _sub(pai, "contribuinteDestinatario")
    ident = _sub(dest, "identificacao")

    if cnpj:
        _sub(ident, "CNPJ", cnpj)
    elif cpf:
        _sub(ident, "CPF", cpf)
    elif ie:
        _sub(ident, "IE", ie)

    if g.razao_social_destinatario:
        _sub(dest, "razaoSocial", g.razao_social_destinatario)
    if g.municipio_destinatario:
        _sub(dest, "municipio", g.municipio_destinatario)


# ---------------------------------------------------------------------------
# Construção de um TDadosGNRE completo
# ---------------------------------------------------------------------------

def construir_dado_gnre(g: DifAlGuia) -> etree._Element:
    dado = etree.Element("TDadosGNRE", nsmap=NSMAP)
    dado.set("versao", "2.00")

    _sub(dado, "ufFavorecida", g.uf_favorecida.upper())
    _sub(dado, "tipoGnre", g.tipo_gnre)

    _bloco_emitente(dado, g)

    itens = _sub(dado, "itensGNRE")
    _bloco_item(itens, g)

    _sub(dado, "valorGNRE", _fmt(g.valor_gnre))

    if g.data_pagamento:
        _sub(dado, "dataPagamento", g.data_pagamento)
    elif g.data_vencimento:
        _sub(dado, "dataPagamento", g.data_vencimento)

    if g.identificador_guia:
        _sub(dado, "identificadorGuia", g.identificador_guia)

    return dado


# ---------------------------------------------------------------------------
# Lote completo
# ---------------------------------------------------------------------------

def construir_lote_xml(guias: list[DifAlGuia]) -> str:
    """
    Gera o XML do lote GNRE (até 50 guias).
    Retorna string XML sem declaração <?xml?> (adicionada no envelope SOAP
    ou no momento de salvar em arquivo).
    """
    if len(guias) > 50:
        raise ValueError(f"Máximo 50 guias por lote, recebido {len(guias)}")

    lote = etree.Element("TLote_GNRE", nsmap=NSMAP)
    lote.set("versao", "2.00")

    guias_el = etree.SubElement(lote, "guias")
    for g in guias:
        guias_el.append(construir_dado_gnre(g))

    return etree.tostring(lote, pretty_print=True, xml_declaration=False, encoding="unicode")


def construir_lote_xml_arquivo(guias: list[DifAlGuia]) -> str:
    """
    Versão para salvar em arquivo — inclui declaração XML com standalone='yes',
    exatamente como especificado no manual do portal.
    """
    corpo = construir_lote_xml(guias)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n' + corpo


def dividir_em_lotes(guias: list[DifAlGuia], tamanho: int = 50) -> list[list[DifAlGuia]]:
    return [guias[i : i + tamanho] for i in range(0, len(guias), tamanho)]


# ---------------------------------------------------------------------------
# Envelopes SOAP
# ---------------------------------------------------------------------------

def construir_envelope_soap_recepcao(xml_lote: str) -> bytes:
    SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
    SVC_NS  = "http://www.gnre.pe.gov.br/webservice/GnreLoteRecepcao"

    nsmap    = {"soapenv": SOAP_NS, "gnr": SVC_NS}
    envelope = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap=nsmap)
    etree.SubElement(envelope, f"{{{SOAP_NS}}}Header")
    body      = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    dados_msg = etree.SubElement(body, f"{{{SVC_NS}}}gnreDadosMsg")

    lote_el = etree.fromstring(xml_lote.encode("utf-8"))
    dados_msg.append(lote_el)

    return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding="UTF-8")


def construir_envelope_soap_consulta(protocolo: str) -> bytes:
    SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
    SVC_NS  = "http://www.gnre.pe.gov.br/webservice/GnreResultadoLote"

    nsmap    = {"soapenv": SOAP_NS, "gnr": SVC_NS}
    envelope = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap=nsmap)
    etree.SubElement(envelope, f"{{{SOAP_NS}}}Header")
    body      = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    dados_msg = etree.SubElement(body, f"{{{SVC_NS}}}gnreDadosMsg")

    cons = etree.SubElement(dados_msg, "TConsLoteGNRE", nsmap=NSMAP)
    cons.set("versao", "2.00")
    _sub(cons, "numeroProtocolo", protocolo)

    return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding="UTF-8")
