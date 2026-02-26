import re
from .base_model import BaseInventoryModel

class ModeloP72(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        for linha in linhas:
            linha = linha.strip()

            # REGRA DE OURO: Se não começa com número (NCM), ignora a linha na hora
            if not linha or not linha[0].isdigit():
                continue

            # REGEX SIMPLIFICADA:
            # ^(\d{8})    -> NCM (8 dígitos) no início
            # \s+.*?      -> Pula a descrição (não captura mais)
            # \s+([A-ZÇP]{1,2}) -> Unidade (UN, PÇ, etc)
            # \s+([\d.,]+) -> Quantidade
            # \s+([\d.,]+) -> Custo
            # \s+([\d.,]+)$ -> Total
            match = re.search(r'^(\d{8})\s+.*?\s+([A-ZÇP]{1,2})\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)$', linha)
            
            if match:
                dados_finais.append({
                    "NCM": match.group(1),
                    "UN": match.group(2),
                    "Quantidade": match.group(3),
                    "Custo": match.group(4),
                    "Total": match.group(5)
                })
                
        return dados_finais