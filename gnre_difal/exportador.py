"""
Exporta os resultados do processamento dos lotes GNRE para Excel.
"""

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from gnre_difal.models import DifAlGuia, RetornoGuia

logger = logging.getLogger(__name__)


def salvar_resultados(
    guias: list[DifAlGuia],
    resultados: list[RetornoGuia],
    diretorio_saida: str | Path,
    sufixo: str = "",
) -> Path:
    """
    Gera um arquivo Excel com os dados enviados + resultado do processamento.
    Retorna o caminho do arquivo gerado.
    """
    diretorio_saida = Path(diretorio_saida)
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"resultado_gnre_{timestamp}{sufixo}.xlsx"
    caminho = diretorio_saida / nome_arquivo

    # Monta DataFrame de envios
    rows_envio = []
    for g in guias:
        rows_envio.append({
            "UF Favorecida": g.uf_favorecida,
            "CNPJ Emitente": g.cnpj_emitente,
            "Razão Social": g.razao_social,
            "Período": g.periodo_referencia,
            "Receita": g.codigo_receita,
            "Valor Principal ICMS": float(g.valor_principal),
            "Valor FECP": float(g.valor_fecp),
            "Juros": float(g.valor_juros),
            "Multa": float(g.valor_multa),
            "Total GNRE": float(g.valor_gnre),
            "Vencimento": g.data_vencimento,
            "Doc Origem": g.documento_origem or "",
        })
    df_envio = pd.DataFrame(rows_envio)

    # Monta DataFrame de retornos
    rows_ret = []
    for r in resultados:
        rows_ret.append({
            "UF": r.uf,
            "Situação": r.situacao,
            "Mensagem": r.mensagem,
            "Código de Barras": r.codigo_barras or "",
            "Linha Digitável": r.linha_digitavel or "",
            "Valor": float(r.valor) if r.valor else "",
            "Vencimento": r.vencimento or "",
        })
    df_ret = pd.DataFrame(rows_ret) if rows_ret else pd.DataFrame()

    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df_envio.to_excel(writer, sheet_name="Guias Enviadas", index=False)
        if not df_ret.empty:
            df_ret.to_excel(writer, sheet_name="Resultados", index=False)

    logger.info("Resultado salvo em: %s", caminho)
    return caminho


def salvar_log_protocolos(
    protocolos: list[dict],
    diretorio_saida: str | Path,
) -> Path:
    """Salva um CSV com todos os protocolos gerados no processamento."""
    diretorio_saida = Path(diretorio_saida)
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = diretorio_saida / f"protocolos_{timestamp}.csv"

    df = pd.DataFrame(protocolos)
    df.to_csv(caminho, index=False, encoding="utf-8-sig")

    logger.info("Protocolos salvos em: %s", caminho)
    return caminho
