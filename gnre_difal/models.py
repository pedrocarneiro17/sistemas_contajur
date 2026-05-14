from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


# Códigos de receita DIFAL — 6 dígitos numéricos (sem hífen)
# 100080 = ICMS DIFAL (EC 87/2015)
# 100100 = FECP / FCP (Fundo de Combate à Pobreza) — estados que cobram separado
CODIGO_RECEITA_DIFAL: dict[str, str] = {
    "AC": "100080", "AL": "100080", "AM": "100080", "AP": "100080",
    "BA": "100080", "CE": "100080", "DF": "100080", "ES": "100080",
    "GO": "100080", "MA": "100080", "MG": "100080", "MS": "100080",
    "MT": "100080", "PA": "100080", "PB": "100080", "PE": "100080",
    "PI": "100080", "PR": "100080", "RJ": "100080", "RN": "100080",
    "RO": "100080", "RR": "100080", "RS": "100080", "SC": "100080",
    "SE": "100080", "SP": "100080", "TO": "100080",
}

CODIGO_RECEITA_FCP: dict[str, str] = {
    "AL": "100100", "BA": "100100", "CE": "100100", "MA": "100100",
    "MG": "100100", "PB": "100100", "PE": "100100", "PI": "100100",
    "RJ": "100100", "SE": "100100",
}


@dataclass
class DifAlGuia:
    """
    Representa uma guia GNRE de DIFAL conforme estrutura TDadosGNRE v2.00.

    Campos obrigatórios:
      uf_favorecida, cnpj_emitente, razao_social, uf_emitente,
      municipio_emitente, periodo_referencia, valor_principal, data_vencimento
    """

    # --- Identificação da guia ---
    uf_favorecida: str          # UF destinatária (2 chars, ex: "SP")
    tipo_gnre: str = "0"        # 0=Simples | 1=Múlt. documentos | 2=Múlt. receitas

    # --- Emitente ---
    cnpj_emitente: str = ""
    cpf_emitente: str = ""
    ie_emitente: str = ""       # IE na UF favorecida (se inscrito lá)
    razao_social: str = ""
    endereco: str = ""
    municipio_emitente: str = ""  # Código IBGE 5 dígitos (sem prefixo de estado)
    uf_emitente: str = ""         # UF do emitente (estado da empresa)
    cep: str = ""
    telefone: str = ""

    # --- Item (receita) ---
    receita: str = ""           # 6 dígitos. Vazio = usa padrão da UF (100080)
    periodo_referencia: str = ""  # AAAAMM → será separado em mes + ano no XML

    data_vencimento: str = ""   # AAAA-MM-DD
    valor_principal: Decimal = Decimal("0.00")   # tipo="11" (ICMS)
    valor_fecp: Decimal = Decimal("0.00")        # tipo="12" (FCP/FECP, se houver)
    valor_juros: Decimal = Decimal("0.00")       # encargos (somados no total)
    valor_multa: Decimal = Decimal("0.00")

    # --- Destinatário (quando exigido pela UF) ---
    cnpj_destinatario: str = ""
    cpf_destinatario: str = ""
    ie_destinatario: str = ""
    razao_social_destinatario: str = ""
    municipio_destinatario: str = ""

    # --- Outros campos opcionais ---
    detalhamento_receita: str = ""    # código exigido por certas UFs (ex: "1", "2")
    documento_origem_tipo: str = ""   # código do tipo (ex: "55" = NF-e)
    documento_origem: str = ""        # número/chave do documento
    data_pagamento: str = ""          # AAAA-MM-DD (data prevista de pagamento)
    identificador_guia: str = ""      # número identificador no lote (até 10 dígitos)

    # --- Campos extras (máx 3) ---
    campos_extras: list[tuple[str, str]] = None  # [(codigo, valor), ...]

    def __post_init__(self):
        if self.campos_extras is None:
            self.campos_extras = []

    @property
    def codigo_receita(self) -> str:
        return self.receita or CODIGO_RECEITA_DIFAL.get(self.uf_favorecida, "100080")

    @property
    def mes_referencia(self) -> str:
        """Retorna MM do periodo_referencia (AAAAMM)."""
        return self.periodo_referencia[4:6] if len(self.periodo_referencia) == 6 else ""

    @property
    def ano_referencia(self) -> str:
        """Retorna AAAA do periodo_referencia (AAAAMM)."""
        return self.periodo_referencia[:4] if len(self.periodo_referencia) == 6 else ""

    @property
    def total_icms(self) -> Decimal:
        return self.valor_principal + self.valor_juros + self.valor_multa

    @property
    def total_fecp(self) -> Decimal:
        return self.valor_fecp

    @property
    def valor_gnre(self) -> Decimal:
        return self.total_icms + self.total_fecp


@dataclass
class RetornoProtocolo:
    protocolo: str
    situacao: str
    mensagem: str = ""


@dataclass
class RetornoGuia:
    numero_guia: Optional[str] = None
    codigo_barras: Optional[str] = None
    linha_digitavel: Optional[str] = None
    situacao: str = ""
    mensagem: str = ""
    uf: str = ""
    valor: Optional[Decimal] = None
    vencimento: Optional[str] = None
