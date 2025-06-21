from pathlib import Path
import fitz  # PyMuPDF

def validate_pdf(file):
    """
    Valida se o arquivo fornecido é um PDF verificando sua extensão.
    """
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

def read_pdf2(file):
    """
    Lê um arquivo PDF e extrai o texto de todas as páginas como um fluxo contínuo.
    Retorna o texto extraído ou levanta uma exceção se o arquivo for inválido.
    """
    if not validate_pdf(file):
        raise ValueError("O arquivo fornecido não é um PDF válido.")
    
    text = ""
    try:
        # Garantir que estamos no início do arquivo
        if hasattr(file, 'seek'):
            file.seek(0)
            
        file_content = file.read()
        
        # Reset do ponteiro se possível
        if hasattr(file, 'seek'):
            file.seek(0)
            
        with fitz.open(stream=file_content, filetype="pdf") as pdf:
            for page in pdf:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
                    
        if not text.strip():
            raise ValueError("Nenhum texto foi extraído do PDF.")
            
        return text
        
    except Exception as e:
        raise Exception(f"Erro ao ler o PDF: {str(e)}")