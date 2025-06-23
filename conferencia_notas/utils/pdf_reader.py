import pdfplumber

def read_pdf_and_identify_model(pdf_path):
    """
    Lê o PDF e identifica o modelo com base no conteúdo.
    Retorna o modelo ('Bling' ou 'Unknown') e o texto bruto.
    """
    texto_completo = ''
    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            pagina_texto = pagina.extract_text()
            if pagina_texto:
                texto_completo += pagina_texto + '\n'
    
    # Identificar modelo com base na palavra "bling"
    if 'bling' in texto_completo.lower():
        modelo = 'Bling'
    elif 'sgbr sistemas' in texto_completo.lower():
        modelo = 'SGBr Sistemas'
    elif 'Relatório Fechamento Fiscal Entradas' in texto_completo:
        modelo = 'Relatório Fechamento Fiscal Entradas'
    else:
        modelo = 'Unknown'
    
    return modelo, texto_completo