from pathlib import Path
import pdfplumber
from .identificador import identificar_banco

def validate_pdf(file):
    """Valida se o arquivo é um PDF válido."""
    if file is None:
        return False
    
    # Para Flask: usar filename em vez de name
    if hasattr(file, 'filename'):
        file_name = file.filename
    elif hasattr(file, 'name'):
        file_name = file.name
    else:
        return False
    
    if not file_name:
        return False
        
    return Path(file_name).suffix.lower() == '.pdf'

def read_pdf(file):
    """
    Extrai texto de um PDF e identifica o banco.
    Retorna uma tupla com (texto, nome_banco) ou levanta exceção em caso de erro.
    """
    if not validate_pdf(file):
        return None, "Arquivo não é um PDF válido"
    
    try:
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            return None, "Nenhum texto extraído do PDF"
        
        banco_identificado = identificar_banco(text)
        return text, banco_identificado
        
    except Exception as e:
        return None, f"Erro ao processar PDF: {str(e)}"