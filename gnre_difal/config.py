"""
Configurações da automação GNRE/DIFAL.
Preencha este arquivo ou use variáveis de ambiente / arquivo .env.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Identificação da empresa emitente
# ---------------------------------------------------------------------------
CNPJ_EMITENTE: str = os.getenv("CNPJ_EMITENTE", "")          # Somente números
IE_EMITENTE: str | None = os.getenv("IE_EMITENTE", None)      # None = ISENTO

# ---------------------------------------------------------------------------
# Certificado digital eCNPJ (A1 ou A3)
# ---------------------------------------------------------------------------
CERT_PATH: str = os.getenv("CERT_PATH", "certificado.pfx")    # Caminho do .pfx
CERT_PASSWORD: str = os.getenv("CERT_PASSWORD", "")           # Senha do certificado

# ---------------------------------------------------------------------------
# Endpoints GNRE (produção)
# ---------------------------------------------------------------------------
URL_LOTE_RECEPCAO: str = "https://www.gnre.pe.gov.br/gnreWS/services/GnreLoteRecepcao"
URL_LOTE_RESULTADO: str = "https://www.gnre.pe.gov.br/gnreWS/services/GnreResultadoLote"
URL_CONFIG_UF: str = "https://www.gnre.pe.gov.br/gnreWS/services/GnreConfigUF"

# Para homologação (ambiente de testes), descomente e ajuste:
# URL_LOTE_RECEPCAO = "https://www.testegnre.pe.gov.br/gnreWS/services/GnreLoteRecepcao"
# URL_LOTE_RESULTADO = "https://www.testegnre.pe.gov.br/gnreWS/services/GnreResultadoLote"
# URL_CONFIG_UF = "https://www.testegnre.pe.gov.br/gnreWS/services/GnreConfigUF"

# ---------------------------------------------------------------------------
# Limites do portal (não alterar)
# ---------------------------------------------------------------------------
MAX_GUIAS_POR_LOTE: int = 50
MAX_ITENS_POR_LOTE: int = 300

# ---------------------------------------------------------------------------
# Parâmetros de processamento
# ---------------------------------------------------------------------------
TIMEOUT_SEGUNDOS: int = 60
TENTATIVAS_CONSULTA: int = 5        # quantas vezes tenta consultar o resultado
INTERVALO_CONSULTA_SEGUNDOS: int = 10

# ---------------------------------------------------------------------------
# Arquivos de entrada e saída
# ---------------------------------------------------------------------------
ARQUIVO_ENTRADA: str = os.getenv("ARQUIVO_ENTRADA", "dados_difal.xlsx")
DIRETORIO_SAIDA: str = os.getenv("DIRETORIO_SAIDA", "saida")
