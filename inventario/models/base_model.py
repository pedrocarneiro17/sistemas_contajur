import pandas as pd

class BaseInventoryModel:
    def __init__(self, text):
        """
        Recebe o texto bruto do PDF extraído pelo pdfplumber.
        """
        self.text = text

    def to_csv(self, data, output_path):
        """
        Transforma a lista de dicionários em um arquivo CSV.
        """
        if not data:
            return False
            
        df = pd.DataFrame(data)
        
        # Salvando com ; como separador (padrão Excel Brasil) 
        # e utf-8-sig para não dar erro de acentuação no Excel
        df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
        return True