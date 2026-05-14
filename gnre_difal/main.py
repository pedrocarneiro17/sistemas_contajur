"""
Automação GNRE/DIFAL — Ponto de entrada principal.

Uso:
    python main.py                        # usa config.py (ARQUIVO_ENTRADA)
    python main.py dados.xlsx             # arquivo específico
    python main.py dados.xlsx --dry-run   # gera XMLs sem enviar
"""

import argparse
import logging
import sys
from pathlib import Path

import config
from exportador import salvar_log_protocolos, salvar_resultados
from leitor_dados import ler_planilha
from models import DifAlGuia, RetornoGuia
from soap_client import GnreClient
from xml_builder import (
    construir_envelope_soap_consulta,
    construir_envelope_soap_recepcao,
    construir_lote_xml,
    construir_lote_xml_arquivo,
    dividir_em_lotes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("gnre_difal.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def salvar_xmls_locais(lotes: list[list[DifAlGuia]], diretorio: str | Path) -> None:
    """Grava os XMLs dos lotes em disco para auditoria / envio manual ao portal."""
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    for i, lote in enumerate(lotes, 1):
        # construir_lote_xml_arquivo inclui <?xml ... standalone="yes"?>
        xml = construir_lote_xml_arquivo(lote)
        path = diretorio / f"lote_{i:03d}.xml"
        path.write_text(xml, encoding="utf-8")
        logger.info("XML lote %d salvo: %s", i, path)


def processar(arquivo_entrada: str, dry_run: bool = False) -> None:
    logger.info("=" * 60)
    logger.info("Iniciando processamento GNRE/DIFAL")
    logger.info("Arquivo: %s | Dry-run: %s", arquivo_entrada, dry_run)
    logger.info("=" * 60)

    # 1. Lê as guias da planilha
    guias = ler_planilha(arquivo_entrada)
    if not guias:
        logger.error("Nenhuma guia válida encontrada. Encerrando.")
        return

    logger.info("Total de guias a processar: %d", len(guias))

    # 2. Divide em lotes (máx. 50 guias)
    lotes = dividir_em_lotes(guias, tamanho=config.MAX_GUIAS_POR_LOTE)
    logger.info("Lotes gerados: %d", len(lotes))

    # 3. Salva XMLs localmente para auditoria
    dir_saida = Path(config.DIRETORIO_SAIDA)
    salvar_xmls_locais(lotes, dir_saida / "xmls")

    if dry_run:
        logger.info("Modo dry-run: XMLs gerados em '%s'. Envio cancelado.", dir_saida / "xmls")
        return

    # 4. Envia lotes e coleta protocolos
    log_protocolos = []
    resultados_totais: list[RetornoGuia] = []

    with GnreClient() as cliente:
        for num_lote, lote in enumerate(lotes, 1):
            logger.info("--- Lote %d/%d (%d guias) ---", num_lote, len(lotes), len(lote))

            try:
                xml_lote = construir_lote_xml(lote)
                envelope_envio = construir_envelope_soap_recepcao(xml_lote)

                retorno = cliente.enviar_lote(envelope_envio)

                log_protocolos.append({
                    "lote": num_lote,
                    "protocolo": retorno.protocolo,
                    "situacao": retorno.situacao,
                    "mensagem": retorno.mensagem,
                    "guias": len(lote),
                })

                if retorno.protocolo:
                    logger.info("Protocolo %s — consultando resultado...", retorno.protocolo)
                    envelope_consulta = construir_envelope_soap_consulta(retorno.protocolo)
                    guias_retorno = cliente.consultar_com_retry(envelope_consulta)
                    resultados_totais.extend(guias_retorno)
                    logger.info("Retorno: %d guias processadas no lote %d", len(guias_retorno), num_lote)
                else:
                    logger.warning("Lote %d: protocolo não retornado. Situação: %s", num_lote, retorno.situacao)

            except Exception as e:
                logger.error("Erro no lote %d: %s", num_lote, e)
                log_protocolos.append({
                    "lote": num_lote,
                    "protocolo": "",
                    "situacao": "ERRO",
                    "mensagem": str(e),
                    "guias": len(lote),
                })

    # 5. Exporta resultados
    if log_protocolos:
        salvar_log_protocolos(log_protocolos, dir_saida)

    if resultados_totais or guias:
        salvar_resultados(guias, resultados_totais, dir_saida)

    logger.info("Processamento concluído. Resultados em: %s", dir_saida)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automação GNRE/DIFAL em lote")
    parser.add_argument(
        "arquivo",
        nargs="?",
        default=config.ARQUIVO_ENTRADA,
        help="Planilha com os dados DIFAL (xlsx ou csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Gera os XMLs sem enviar ao portal",
    )
    args = parser.parse_args()

    processar(args.arquivo, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
