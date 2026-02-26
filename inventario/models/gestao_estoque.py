import re
from .base_model import BaseInventoryModel

class GestaoEstoque(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        # O erro estava aqui: mude de "lines" para "linhas"
        for linha in linhas:
            linha = linha.strip()
            
            if not linha or any(x in linha for x in ["Gestão de Estoque", "CÓDIGO DESCRIÇÃO", "CPF/CNPJ:"]):
                continue

            # Regex mantida conforme a lógica anterior
            match = re.search(r'^(\S+)\s+.*?\s+(\d{8})\s+(\d+)\s+R\$\s+([\d.,]+)\s+R\$\s+([\d.,]+)$', linha)
            
            if match:
                dados_finais.append({
                    "Codigo": match.group(1),
                    "NCM": match.group(2),
                    "Estoque": match.group(3),
                    "Valor_Custo": match.group(4),
                    "Valor_Venda": match.group(5),
                })
        
        return dados_finais