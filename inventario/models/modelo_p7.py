import re
from .base_model import BaseInventoryModel

class ModeloP7(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        pode_ler = False
        
        for linha in linhas:
            linha = linha.strip()
            
            if "CST/CSOSN NCM Discriminação" in linha:
                pode_ler = True
                continue
            
            if "Total Geral" in linha:
                break
            
            if not linha or "LIVRO REGISTRO" in linha or "FIRMA:" in linha:
                continue
                
            if pode_ler:
                # REGEX AJUSTADA:
                # 1. ^(\d{3})  -> CST
                # 2. \s+(\d{8}) -> NCM
                # 3. \s+.*?    -> Pula a Descrição (não capturamos mais o grupo)
                # 4. \s+(\w{2,3}) -> Unidade
                # 5. \s+([\d.,]+) -> Quantidade
                # 6. \s+([\d.,]+) -> Valor Unitário
                # 7. \s+([\d.,]+)$ -> Valor Total
                match = re.search(r'^(\d{3})\s+(\d{8})\s+.*?\s+(\w{2,3})\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)$', linha)
                
                if match:
                    dados_finais.append({
                        "CST_CSOSN": match.group(1),
                        "NCM": match.group(2),
                        "Unidade": match.group(3),
                        "Quantidade": match.group(4),
                        "Valor_Unitario": match.group(5),
                        "Valor_Total": match.group(6)
                    })
        
        return dados_finais