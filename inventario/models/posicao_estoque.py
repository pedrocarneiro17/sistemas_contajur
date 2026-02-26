import re
from .base_model import BaseInventoryModel

class PosicaoEstoque(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        for linha in linhas:
            linha = linha.strip()
            
            # 1. Filtros de descarte (Cabeçalho, Rodapé e Filtros)
            if any(x in linha for x in ["Posição de Estoque", "Código Descrição", "MURIÉRICA", "Filtro:", "Pág."]):
                continue

            # 2. REGEX PARA O MODELO:
            # ^(\S+)      -> Grupo 1: Código (Pega tudo até o primeiro espaço, ex: 825, DL0845-00)
            # \s+         -> Espaço
            # .*?         -> Pula a Descrição (non-greedy)
            # 0,00\s+0,00 -> Pula os campos fixos R$ Médio e Tot. Médio
            # \s+         -> Espaço
            # ([\d.]+,\d+|\d+) -> Grupo 2: Quantidade (Pode ser 10 ou 10,00)
            # \s+         -> Espaço
            # ([\d.]+,\d+) -> Grupo 3: Custo Unitário
            # \s+         -> Espaço
            # ([\d.]+,\d+)$ -> Grupo 4: Total Final
            match = re.search(r'^(\S+)\s+.*?\s+0,00\s+0,00\s+([\d.]+,\d+|\d+)\s+([\d.]+,\d+)\s+([\d.]+,\d+)$', linha)
            
            if match:
                dados_finais.append({
                    "Codigo": match.group(1),
                    "Quantidade": match.group(2),
                    "Custo": match.group(3),
                    "Total": match.group(4)
                })
        
        return dados_finais