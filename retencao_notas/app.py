import os
from flask import Blueprint, request, jsonify, send_file, render_template # Adicionado render_template
import requests
import json
from pdfminer.high_level import extract_text # Importar extract_text do pdfminer.six
import tempfile # Para lidar com arquivos temporários
import logging

# Configurar o logging (apenas erros)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Configurar o Blueprint
retencao_bp = Blueprint('retencao_notas', __name__, url_prefix='/retencao_notas')

# Substitua pela sua chave de API Gemini real
GEMINI_API_KEY = "AIzaSyA0hJdqhpW0cyaZ6K_ezA82lTMJWOiRO44" # Usando a chave fornecida pelo usuário

def extract_text_from_pdf(pdf_path):
    """
    Extrai texto de um arquivo PDF usando pdfminer.six para extração direta.
    Args:
        pdf_path (str): O caminho para o arquivo PDF.
    Returns:
        str: O texto extraído do PDF.
    """
    try:
        text = extract_text(pdf_path)
        if text and len(text.strip()) > 0: # Verifica se algum texto foi extraído
            logger.info(f"Texto extraído diretamente de {pdf_path}.")
            return text
        else:
            logger.warning(f"Nenhum texto extraído diretamente de {pdf_path}.")
            return None
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF {pdf_path}: {e}")
        return None

def process_pdf_with_gemini(pdf_text, api_key):
    """
    Processa o texto do PDF usando a API Gemini para extrair informações.
    Args:
        pdf_text (str): O texto extraído do PDF.
        api_key (str): A chave da API Gemini.
    Returns:
        dict: Um dicionário contendo o nome da empresa e as retenções, ou None em caso de erro.
    """
    if not pdf_text:
        return None

    prompt = (
        "Analise o seguinte texto de nota fiscal em português e extraia as seguintes informações:\n"
        "1. O nome da empresa (Prestador de Serviços ou Tomador de Serviços, o mais relevante para a nota).\n"
        "2. Uma lista de todas as retenções mencionadas, com seus respectivos valores. "
        "Procure por termos como 'Retenções Federais', 'ISS Retido na Fonte', 'Valor ISS', 'Valor Retido IR', 'INSS', 'CSLL', 'IRRF', 'COFINS', 'PIS/PASEP', 'Outras retenções' e seus valores correspondentes.\n\n"
        "Texto da Nota Fiscal:\n"
        f"{pdf_text}"
    )

    chat_history = []
    chat_history.append({ "role": "user", "parts": [{ "text": prompt }] })

    payload = {
        "contents": chat_history,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "company_name": {"type": "STRING"},
                    "retentions": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "type": {"type": "STRING"},
                                "value": {"type": "STRING"}
                            },
                            "propertyOrdering": ["type", "value"]
                        }
                    }
                },
                "propertyOrdering": ["company_name", "retentions"]
            }
        }
    }

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    try:
        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
            json_str = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed_json = json.loads(json_str)
            return parsed_json
        else:
            logger.error(f"Estrutura de resposta inesperada da API Gemini: {result}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição à API Gemini: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON da API Gemini: {e}\nResposta bruta: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado ao processar com Gemini: {e}")
        return None


@retencao_bp.route('/')
def retencao_notas():
    """
    Rota para renderizar a página de upload de Notas Fiscais a partir de um template HTML.
    """
    return render_template('retencao_notas.html') # <--- Retorna o template HTML


@retencao_bp.route('/upload', methods=['POST'])
def upload_pdfs():
    """
    Rota para fazer upload de arquivos PDF, extrair o texto, gerar um TXT bruto
    e, em seguida, processar com a API Gemini para gerar o relatório final.
    Todos os arquivos intermediários são temporários e serão removidos.
    """
    if 'pdfs' not in request.files:
        logger.error("Nenhum arquivo 'pdfs' fornecido.")
        return "Erro: Nenhum arquivo 'pdfs' fornecido.", 400

    uploaded_files = request.files.getlist('pdfs')
    if not uploaded_files:
        logger.error("Nenhum arquivo selecionado para upload.")
        return "Erro: Nenhum arquivo selecionado.", 400

    report_content = []
    temp_files_to_clean = [] # Lista unificada para todos os arquivos temporários

    try:
        for pdf_file in uploaded_files:
            if pdf_file.filename == '':
                continue

            tmp_pdf_path = None
            tmp_raw_text_path = None
            try:
                # Cria um arquivo temporário para o PDF de upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(pdf_file.read())
                    tmp_pdf_path = tmp_pdf.name
                    temp_files_to_clean.append(tmp_pdf_path)
                
                logger.info(f"Arquivo PDF salvo temporariamente: {tmp_pdf_path}")

                pdf_text = extract_text_from_pdf(tmp_pdf_path)
                
                if pdf_text and len(pdf_text.strip()) >= 300:
                    # Cria um arquivo temporário para o texto bruto extraído
                    with tempfile.NamedTemporaryFile(delete=False, suffix="_extracted_raw.txt", mode='w', encoding='utf-8') as tmp_raw_text_file:
                        tmp_raw_text_file.write(pdf_text)
                        tmp_raw_text_path = tmp_raw_text_file.name
                        temp_files_to_clean.append(tmp_raw_text_path)
                    logger.info(f"Texto bruto extraído salvo temporariamente em: {tmp_raw_text_path}")

                    extracted_data = process_pdf_with_gemini(pdf_text, GEMINI_API_KEY)
                    if extracted_data:
                        report_content.append(f"--- Relatório para: {pdf_file.filename} ---")
                        report_content.append(f"Nome da Empresa: {extracted_data.get('company_name', 'Não encontrado')}")
                        report_content.append("Retenções:")
                        if extracted_data.get('retentions'):
                            for retention in extracted_data['retentions']:
                                report_content.append(f"  - Tipo: {retention.get('type', 'N/A')}, Valor: {retention.get('value', 'N/A')}")
                        else:
                            report_content.append("  Nenhuma retenção encontrada.")
                        report_content.append("\n")
                    else:
                        report_content.append(f"--- Erro ao processar {pdf_file.filename} com a API Gemini ---")
                        report_content.append("\n")
                else:
                    report_content.append(f"--- Relatório para: {pdf_file.filename} ---")
                    report_content.append(f"Não foi possível extrair texto suficiente (menos de 300 caracteres) do arquivo '{pdf_file.filename}'.")
                    report_content.append("Por favor, verifique se o PDF contém texto selecionável.")
                    report_content.append("\n")

            except Exception as e:
                logger.error(f"Erro inesperado ao processar o arquivo {pdf_file.filename}: {e}")
                report_content.append(f"--- Erro ao processar {pdf_file.filename} ---")
                report_content.append(f"Ocorreu um erro inesperado: {str(e)}")
                report_content.append("\n")
            finally:
                if tmp_pdf_path and os.path.exists(tmp_pdf_path):
                    try:
                        os.unlink(tmp_pdf_path)
                        logger.info(f"Arquivo PDF temporário removido: {tmp_pdf_path}")
                    except Exception as e:
                        logger.warning(f"Falha ao remover arquivo PDF temporário {tmp_pdf_path}: {e}")

        final_report_path = None
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_report_file:
            tmp_report_file.write("\n".join(report_content))
            final_report_path = tmp_report_file.name
            temp_files_to_clean.append(final_report_path)

        return send_file(final_report_path, as_attachment=True, download_name="relatorio_notas_fiscais.txt", mimetype='text/plain')

    finally:
        for path in temp_files_to_clean:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.info(f"Arquivo temporário removido: {path}")
                except Exception as e:
                    logger.warning(f"Falha ao remover arquivo temporário {path}: {e}")
