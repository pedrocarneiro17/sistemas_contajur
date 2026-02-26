import re
from .base_model import BaseInventoryModel

class ModeloListagemSimples(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        # Padrão simplificado: 
        # Código + Pula tudo até os números + Qtd + (Un) + Valor + Total
        # O (Un) ajuda a marcar onde terminam os números de quantidade
        padrao_item = r'(\d+.*?\s+[\d.,]+\s?\(.*?\)\s+[\d.,]+\s+[\d.,]+)'
        
        for linha in linhas:
            if any(x in linha for x in ["Listagem Simples", "Cód. Produto", "Thotau:", "Pág.:"]):
                continue

            itens_na_linha = re.findall(padrao_item, linha)
            
            for item in itens_na_linha:
                item = item.strip()
                
                # REGEX SEM DESCRIÇÃO:
                # 1. ^(\d+)    -> Código
                # 2. .*?\s+    -> Pula a descrição até o último espaço antes da Qtd
                # 3. ([\d.,]+) -> Quantidade
                # 4. \s?\(.*?\) -> Pula o (Un) ou ( UN)
                # 5. \s+([\d.,]+) -> Valor Unitário
                # 6. \s+([\d.,]+)$ -> Valor Total
                match = re.search(r'^(\d+).*?\s+([\d.,]+)\s?\(.*?\)\s+([\d.,]+)\s+([\d.,]+)$', item)
                
                if match:
                    dados_finais.append({
                        "Codigo": match.group(1),
                        "Quantidade": match.group(2),
                        "Valor_Unitario": match.group(3),
                        "Valor_Total": match.group(4)
                    })
        
        return dados_finais