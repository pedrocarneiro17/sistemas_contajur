"""
Cliente SOAP para os web services GNRE.
Usa requests com certificado eCNPJ (client certificate mutual TLS).
"""

import time
import logging
from pathlib import Path
from decimal import Decimal

import requests
from lxml import etree

import gnre_difal.config as config
from gnre_difal.certificate import montar_sessao_com_certificado, limpar_pem_temporarios
from gnre_difal.models import RetornoProtocolo, RetornoGuia

logger = logging.getLogger(__name__)

HEADERS_SOAP = {
    "Content-Type": "text/xml; charset=UTF-8",
    "SOAPAction": "",
}

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


class GnreClient:
    def __init__(self) -> None:
        self._cert_pem: str | None = None
        self._key_pem: str | None = None
        self._session: requests.Session | None = None

    def __enter__(self) -> "GnreClient":
        self._session = requests.Session()
        self._session.verify = True

        ok = montar_sessao_com_certificado(
            self._session, config.CERT_PATH, config.CERT_PASSWORD
        )
        if not ok:
            raise RuntimeError(
                "Não foi possível carregar o certificado digital.\n"
                "Verifique:\n"
                "  • A senha do certificado está correta?\n"
                "  • O arquivo .pfx não está corrompido?\n"
                "  • O Git for Windows está instalado? (inclui openssl)\n"
                "  • O certificado é um eCNPJ A1 válido?"
            )
        return self

    def __exit__(self, *_) -> None:
        if self._session:
            # Limpa PEMs temporários se existirem
            cert = getattr(self._session, "_gnre_pem_cert", None)
            key  = getattr(self._session, "_gnre_pem_key",  None)
            self._session.close()
            limpar_pem_temporarios(cert, key)

    # ------------------------------------------------------------------
    # Envio de lote
    # ------------------------------------------------------------------

    def enviar_lote(self, envelope_soap: str | bytes) -> RetornoProtocolo:
        logger.info("Enviando lote → %s", config.URL_LOTE_RECEPCAO)
        payload = envelope_soap if isinstance(envelope_soap, bytes) else envelope_soap.encode("utf-8")
        resp = self._session.post(
            config.URL_LOTE_RECEPCAO,
            data=payload,
            headers=HEADERS_SOAP,
            timeout=config.TIMEOUT_SEGUNDOS,
        )
        logger.info("HTTP %s | %d bytes recebidos", resp.status_code, len(resp.content))

        # Salva resposta crua em arquivo para diagnóstico
        self._salvar_resposta_raw(resp.text, "recepcao")

        resp.raise_for_status()
        return self._parsear_retorno_recepcao(resp.text)

    def _parsear_retorno_recepcao(self, xml_resposta: str) -> RetornoProtocolo:
        """
        O portal retorna algo como:
          <soapenv:Body>
            <gnreDadosMsg>           ← pode ser texto (string) ou XML embutido
              <TRetLote_GNRE ...>
                <numeroProtocolo>...</numeroProtocolo>
                <situacao>...</situacao>
              </TRetLote_GNRE>
            </gnreDadosMsg>
          </soapenv:Body>
        """
        try:
            root = etree.fromstring(xml_resposta.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            logger.error("Resposta não é XML válido: %s\n%s", e, xml_resposta[:500])
            return RetornoProtocolo(protocolo="", situacao="erro_parse", mensagem=str(e))

        # Extrai o conteúdo útil dentro do Body SOAP
        conteudo = self._extrair_conteudo_body(root)
        if conteudo is None:
            logger.error("Não encontrou conteúdo no Body SOAP:\n%s", xml_resposta[:500])
            return RetornoProtocolo(protocolo="", situacao="erro_body", mensagem="Body vazio")

        protocolo = self._texto(conteudo, "numeroProtocolo")
        situacao  = self._texto(conteudo, "situacao")
        mensagem  = self._texto(conteudo, "mensagem")

        logger.info("Protocolo: '%s' | Situação: '%s' | Msg: '%s'", protocolo, situacao, mensagem)
        return RetornoProtocolo(protocolo=protocolo, situacao=situacao or "recebido", mensagem=mensagem)

    # ------------------------------------------------------------------
    # Consulta de resultado
    # ------------------------------------------------------------------

    def consultar_resultado(self, envelope_soap: str | bytes) -> list[RetornoGuia]:
        logger.info("Consultando resultado → %s", config.URL_LOTE_RESULTADO)
        payload = envelope_soap if isinstance(envelope_soap, bytes) else envelope_soap.encode("utf-8")
        resp = self._session.post(
            config.URL_LOTE_RESULTADO,
            data=payload,
            headers=HEADERS_SOAP,
            timeout=config.TIMEOUT_SEGUNDOS,
        )
        logger.info("HTTP %s | %d bytes recebidos", resp.status_code, len(resp.content))
        self._salvar_resposta_raw(resp.text, "resultado")
        resp.raise_for_status()
        return self._parsear_resultado(resp.text)

    def _parsear_resultado(self, xml_resposta: str) -> list[RetornoGuia]:
        guias: list[RetornoGuia] = []
        try:
            root = etree.fromstring(xml_resposta.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            logger.error("Resultado não é XML válido: %s", e)
            return guias

        conteudo = self._extrair_conteudo_body(root)
        if conteudo is None:
            return guias

        # Cada guia processada fica em <guia> ou <TDadosGNRE> no retorno
        for guia_el in conteudo.iter():
            tag = etree.QName(guia_el.tag).localname if guia_el.tag else ""
            if tag not in ("guia", "TDadosGNRE"):
                continue

            retorno = RetornoGuia()
            retorno.codigo_barras   = self._texto(guia_el, "codigoBarras")
            retorno.linha_digitavel = self._texto(guia_el, "linhaDigitavel")
            retorno.situacao        = self._texto(guia_el, "situacao") or ""
            retorno.mensagem        = self._texto(guia_el, "mensagem") or ""
            retorno.uf              = self._texto(guia_el, "ufFavorecida") or self._texto(guia_el, "uf") or ""
            retorno.vencimento      = self._texto(guia_el, "dataVencimento")

            valor_txt = self._texto(guia_el, "valorGNRE") or self._texto(guia_el, "valor")
            if valor_txt:
                try:
                    retorno.valor = Decimal(valor_txt)
                except Exception:
                    pass

            guias.append(retorno)

        return guias

    def consultar_com_retry(self, envelope_soap: str | bytes) -> list[RetornoGuia]:
        for tentativa in range(1, config.TENTATIVAS_CONSULTA + 1):
            logger.info("Consulta tentativa %d/%d", tentativa, config.TENTATIVAS_CONSULTA)
            guias = self.consultar_resultado(envelope_soap)
            if guias:
                situacoes = {g.situacao for g in guias}
                if "pendente" not in situacoes and "" not in situacoes:
                    return guias
            if tentativa < config.TENTATIVAS_CONSULTA:
                time.sleep(config.INTERVALO_CONSULTA_SEGUNDOS)

        logger.warning("Resultado pendente após %d tentativas", config.TENTATIVAS_CONSULTA)
        return guias if guias else []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extrair_conteudo_body(self, root: etree._Element) -> etree._Element | None:
        """
        Navega pelo envelope SOAP e extrai o conteúdo XML relevante.
        Suporta dois formatos de resposta do portal GNRE:
          1. XML embutido como filho direto do wrapper (gnreRetornoMsg)
          2. XML como texto (string) dentro do wrapper — desserializa automaticamente
        """
        # Localiza o Body SOAP
        body = root.find(f"{{{SOAP_NS}}}Body")
        if body is None:
            body = root  # fallback

        # Percorre filhos do Body até encontrar conteúdo XML
        for filho in body.iter():
            if filho is body:
                continue

            # Caso 1: o filho TEM sub-elementos → é XML embutido
            sub = list(filho)
            if sub:
                # Verifica se algum sub já é o elemento GNRE
                for s in sub:
                    local = etree.QName(s.tag).localname if s.tag else ""
                    if local.startswith("T") or local in ("numeroProtocolo", "situacao"):
                        return filho
                return sub[0]

            # Caso 2: o filho tem TEXTO que parece XML
            texto = (filho.text or "").strip()
            if texto.startswith("<"):
                try:
                    return etree.fromstring(texto.encode("utf-8"))
                except etree.XMLSyntaxError:
                    pass

        return None

    def _texto(self, el: etree._Element, tag: str) -> str:
        """Busca recursivamente a primeira ocorrência de <tag> e retorna seu texto."""
        for filho in el.iter():
            local = etree.QName(filho.tag).localname if filho.tag else ""
            if local == tag:
                return (filho.text or "").strip()
        return ""

    def _salvar_resposta_raw(self, xml: str, prefixo: str) -> None:
        """Grava a resposta bruta do portal em arquivo para diagnóstico."""
        import datetime, os
        try:
            diretorio = Path(config.DIRETORIO_SAIDA) / "debug"
            diretorio.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = diretorio / f"resposta_{prefixo}_{ts}.xml"
            caminho.write_text(xml, encoding="utf-8")
            logger.info("Resposta raw salva em: %s", caminho)
        except Exception as e:
            logger.warning("Não foi possível salvar resposta raw: %s", e)
        # Sempre loga as primeiras linhas no console também
        linhas = xml.strip().splitlines()
        preview = "\n".join(linhas[:30])
        logger.info("=== RESPOSTA RAW (%s) ===\n%s\n%s",
                    prefixo, preview, "..." if len(linhas) > 30 else "")
