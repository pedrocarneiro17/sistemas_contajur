import re
from .base_model import BaseInventoryModel

class ModeloRI(BaseInventoryModel):
    def process(self):
        linhas = self.text.split('\n')
        dados_finais = []
        
        for linha in linhas:
            linha = linha.strip()
            
            # 1. Filtros de descarte (Cabeçalhos, Rodapés e linha de transporte)
            if any(x in linha for x in ["REGISTRO DE INVENTÁRIO", "CNPJ(MF):", "DESCRIÇÃO DO ARTIGO", "de transporte.:"]):
                continue
            
            # 2. Se a linha chegar no Total Geral ou Final, para o processamento
            if "Total" in linha and not any(c.isdigit() for c in linha[:5]):
                break

            # 3. REGEX SEM DESCRIÇÃO:
            # ^(\d{8})    -> Grupo 1: NCM (8 dígitos)
            # \s+         -> Espaço
            # (\S+)       -> Grupo 2: Código Interno (Pega até o primeiro espaço)
            # .*?\s+      -> Pula toda a descrição (preguiçoso)
            # ([\d.,]+)   -> Grupo 3: Quantidade
            # \s+         -> Espaço
            # ([A-ZÇP]{2})-> Grupo 4: Unidade (PC, PR, UN, JG, LT, KT)
            # \s+         -> Espaço
            # ([\d.,]+)   -> Grupo 5: Custo Unitário
            # \s+         -> Espaço
            # ([\d.,]+)$  -> Grupo 6: Custo Total
            match = re.search(r'^(\d{8})\s+(\S+).*?\s+([\d.,]+)\s+([A-ZÇP]{2})\s+([\d.,]+)\s+([\d.,]+)$', linha)
            
            if match:
                dados_finais.append({
                    "NCM": match.group(1),
                    "Codigo_Interno": match.group(2),
                    "Quantidade": match.group(3),
                    "Unidade": match.group(4),
                    "Valor_Unitario": match.group(5),
                    "Valor_Total": match.group(6)
                })
        
        return dados_finais