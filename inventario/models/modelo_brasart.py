import re
from .base_model import BaseInventoryModel

class ModeloBrasArt(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        for linha in linhas:
            linha = linha.strip()
            
            # REGRA: Só processa se a linha começar com o Código (número)
            if not linha or not linha[0].isdigit():
                continue

            # REGEX PARA BRASART:
            # ^(\d+)        -> Código
            # .*?\s+        -> Pula descrição
            # (?:PC|UN|JG)  -> Unidade (apenas para âncora)
            # \s+(-?\d+)\s+ -> Quantidade (aceita negativos)
            # R\$\s+([\d.,]+) -> Preço de Venda
            # \s+R\$\s+     -> Espaço e R$ do custo
            # ([\d.,]+)$    -> Custo Unitário (final da linha)
            
            match = re.search(r'^(\d+).*?\s+(?:PC|UN|JG)\s+(-?\d+)\s+R\$\s+([\d.,]+)\s+R\$\s+([\d.,]+)$', linha)
            
            if match:
                dados_finais.append({
                    "Codigo": match.group(1),
                    "Quantidade": match.group(2),
                    "Preco_Venda": match.group(3),
                    "Custo": match.group(4),
                })
        
        return dados_finais