import re
from .base_model import BaseInventoryModel

class ModeloP73(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        for linha in linhas:
            linha = linha.strip()
            
            # REGRA: Se não começa com número, descartamos a linha
            if not linha or not linha[0].isdigit():
                continue

            # EXPLICAÇÃO DA REGEX:
            # ^(\d+)       -> Grupo 1: Código (Obrigatório no início)
            # .*?          -> Pula qualquer coisa (texto ou espaço) de forma "preguiçosa"
            # ([\d.]+,\d+) -> Grupo 2: Quantidade (formato 0,00 ou 1.000,00)
            # \s+          -> Espaço
            # ([A-ZÇP]{2}) -> Grupo 3: Unidade (Ex: UN, KG, PC, HR)
            # \s+          -> Espaço
            # ([\d.]+,\d+) -> Grupo 4: Valor Unitário
            # \s+          -> Espaço
            # ([\d.]+,\d+) -> Grupo 5: Valor Total
            match = re.search(r'^(\d+).*?([\d.]+,\d+)\s+([A-ZÇP]{2})\s+([\d.]+,\d+)\s+([\d.]+,\d+)$', linha)
            
            if match:
                dados_finais.append({
                    "Codigo": match.group(1),
                    "Quantidade": match.group(2),
                    "Unidade": match.group(3),
                    "Custo_Unitario": match.group(4),
                    "Custo_Total": match.group(5)
                })
        
        return dados_finais