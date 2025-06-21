from io import BytesIO
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def create_xml(data):
    """
    Cria um arquivo XML a partir dos dados extraídos e retorna o XML como BytesIO.
    """
    root = Element("Transactions")
    
    for transaction in data:
        trans_elem = SubElement(root, "Transaction")
        
        date_elem = SubElement(trans_elem, "Data")
        date_elem.text = transaction["Data"]
        
        desc_elem = SubElement(trans_elem, "Descrição")
        desc_elem.text = transaction["Descrição"]
        
        value_elem = SubElement(trans_elem, "Valor")
        value_elem.text = transaction["Valor"]
        
        type_elem = SubElement(trans_elem, "Tipo")
        type_elem.text = transaction["Tipo"]
    
    rough_string = tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    output = BytesIO()
    output.write(pretty_xml.encode('utf-8'))
    output.seek(0)
    
    return output

def create_txt(data):
    """
    Cria um arquivo TXT a partir dos dados extraídos e retorna o TXT como BytesIO.
    """
    txt_content = ""
    for transaction in data:
        txt_content += f"Data: {transaction['Data']}\n"
        txt_content += f"Descrição: {transaction['Descrição']}\n"
        txt_content += f"Valor: {transaction['Valor']}\n"
        txt_content += f"Tipo: {transaction['Tipo']}\n"
        txt_content += "-" * 50 + "\n"
    
    output = BytesIO()
    output.write(txt_content.encode('utf-8'))
    output.seek(0)
    
    return output

def process_transactions(text, preprocess_func, extract_func):
    """
    Processa o texto extraído de um extrato bancário e retorna XML e TXT.
    Args:
        text (str): Texto extraído do extrato.
        preprocess_func (callable): Função de pré-processamento específica do banco.
        extract_func (callable): Função de extração de transações específica do banco.
    Returns:
        tuple: (xml_data, txt_data) ou (None, None, None) se não houver transações.
    """
    transactions = preprocess_func(text)
    data = extract_func(transactions)
    if not data:
        return None, None
    xml_data = create_xml(data)
    txt_data = create_txt(data)
    return xml_data, txt_data