import pandas as pd
from io import BytesIO
from xml.etree.ElementTree import parse

def xml_to_csv(xml_data):
    """
    Converte um arquivo XML em CSV sem cabeçalho, com campos separados por ponto e vírgula e sem aspas,
    retornando o CSV como BytesIO.
    """
    try:
        # Parse do XML
        tree = parse(xml_data)
        root = tree.getroot()
        
        data = []
        for transaction in root.findall("Transaction"):
            # Extrair os dados e limpar, sem envolver em aspas
            data_value = transaction.find("Data").text.strip() if transaction.find("Data") is not None else ""
            desc_value = transaction.find("Descrição").text.replace("\n", " ").strip() if transaction.find("Descrição") is not None else ""
            value_value = transaction.find("Valor").text.strip() if transaction.find("Valor") is not None else ""
            type_value = transaction.find("Tipo").text.strip() if transaction.find("Tipo") is not None else ""
            
            # Adicionar ao dicionário sem aspas
            data.append({
                "Data": data_value,
                "Descrição": desc_value,
                "Valor": value_value,
                "Tipo": type_value
            })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Converter para CSV sem cabeçalho, com separador ponto e vírgula e sem aspas
        output = BytesIO()
        df.to_csv(output, index=False, header=False, encoding='utf-8-sig', sep=';', quoting=None, escapechar=None)
        output.seek(0)
        
        return output
    except Exception as e:
        raise Exception(f"Erro ao converter XML para CSV: {str(e)}")