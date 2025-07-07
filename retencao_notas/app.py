import os
from flask import Blueprint, request, jsonify, send_file, render_template
import requests
import json
from pdfminer.high_level import extract_text # Para PDFs com texto nativo
import tempfile # Para lidar com arquivos temporários
import logging

# Configurar o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurar o Blueprint
retencao_bp = Blueprint('retencao_notas', __name__, url_prefix='/retencao_notas',
                        template_folder='templates',
                        static_folder='static')

# Substitua pela sua chave de API Gemini real
GEMINI_API_KEY = "AIzaSyA0hJdqhpW0cyaZ6K_ezA82lTMJWOiRO44"

# Definir o limiar de caracteres para considerar o texto "suficiente"
TEXT_MIN_LENGTH_FOR_NATIVE_PDF = 300 # Reintroduzido

# --- Funções de Extração de Texto (APENAS PDF NATIVO com verificação de tamanho) ---

def extract_text_from_pdf(pdf_path):
    """
    Tenta extrair texto de um arquivo PDF usando pdfminer.six.
    Retorna o texto extraído (pode ser vazio ou curto) ou None em caso de erro.
    """
    try:
        text = extract_text(pdf_path)
        if text is None:
            logger.warning(f"pdfminer.six retornou None para {pdf_path}.")
            return ""
        
        cleaned_text = text.strip()
        
        # Loga a quantidade de caracteres encontrados
        logger.info(f"Extração com pdfminer.six concluída para: {pdf_path}. Caracteres: {len(cleaned_text)}")
        
        return cleaned_text
    except Exception as e:
        logger.error(f"Erro ao extrair texto com pdfminer.six de {pdf_path}: {e}", exc_info=True)
        return None

# --- Função de Processamento Gemini (Integrada) ---

def process_pdf_with_gemini(pdf_text):
    """
    Processa o texto do PDF usando a API Gemini para extrair informações.
    Args:
        pdf_text (str): O texto extraído do PDF.
    Returns:
        dict: Um dicionário contendo o nome da empresa e as retenções, ou None em caso de erro.
    """
    if not pdf_text:
        logger.warning("Nenhum texto fornecido para a API Gemini.")
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

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    try:
        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
            json_str = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed_json = json.loads(json_str)
            logger.info(f"Dados extraídos com Gemini para {len(pdf_text.strip())} caracteres.")
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


# --- Rotas do Flask (Blueprint) ---

@retencao_bp.route('/')
def retencao_notas_page():
    """
    Rota para renderizar a página de upload de Notas Fiscais a partir de um template HTML.
    """
    return render_template('retencao_notas.html')


@retencao_bp.route('/upload', methods=['POST'])
def upload_pdfs():
    """
    Rota para fazer upload de arquivos PDF, extrair o texto (apenas PDF nativo),
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
            try:
                # 1. Salvar o PDF de upload em um arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(pdf_file.read())
                    tmp_pdf_path = tmp_pdf.name
                    temp_files_to_clean.append(tmp_pdf_path)
                
                logger.info(f"Arquivo PDF '{pdf_file.filename}' salvo temporariamente como: {tmp_pdf_path}")

                # 2. Extrair texto do PDF (APENAS pdfminer.six)
                pdf_text = extract_text_from_pdf(tmp_pdf_path)
                
                # 3. Verificar o comprimento do texto extraído
                if pdf_text and len(pdf_text) >= TEXT_MIN_LENGTH_FOR_NATIVE_PDF:
                    logger.info(f"Texto suficiente ({len(pdf_text)} caracteres) extraído via pdfminer.six para {pdf_file.filename}.")
                    
                    # 4. Processar o texto com a API Gemini
                    extracted_data = process_pdf_with_gemini(pdf_text) 
                    if extracted_data:
                        report_content.append(f"--- Relatório para: {pdf_file.filename} ---")
                        report_content.append(f"Nome da Empresa: {extracted_data.get('company_name', 'Não encontrado')}")
                        report_content.append("Retenções:")
                        if extracted_data.get('retentions'):
                            for retention in extracted_data['retentions']:
                                r_type = retention.get('type', 'N/A')
                                r_value = retention.get('value', 'N/A')

                                # --- LÓGICA DE AJUSTE PARA VALORES DE RETENÇÃO (MANTIDA) ---
                                if r_type == 'Valor Retido IR' and isinstance(r_value, str):
                                    # Remove R$, espaços, e se o primeiro caractere for um dígito (e não -), tenta remover o primeiro dígito
                                    cleaned_value = r_value.replace('R$', '').replace(' ', '').replace(',', '.')
                                    
                                    # Verifica se o primeiro caractere é um dígito e não um sinal de menos
                                    if len(cleaned_value) > 0 and cleaned_value[0].isdigit() and cleaned_value[0] != '-':
                                        cleaned_value = cleaned_value[1:] 
                                        logger.info(f"Ajuste aplicado para '{r_type}': '{r_value}' -> '{cleaned_value}'")
                                    
                                    try:
                                        num_value = float(cleaned_value)
                                        # Heurística para re-adicionar o sinal negativo se o original tinha
                                        if 'R$ -' in retention.get('value', '') and num_value >= 0:
                                            r_value = f"-{num_value:.2f}".replace('.', ',')
                                        else:
                                            r_value = f"{num_value:.2f}".replace('.', ',')
                                            # Se o OCR colocou - mas não deveria, remove. (Ex: -404.21 vira 404.21 se original não tinha -)
                                            if r_value.startswith('-') and 'R$ -' not in retention.get('value', ''):
                                                r_value = r_value.lstrip('-')
                                    except ValueError:
                                        logger.warning(f"Não foi possível converter '{cleaned_value}' para número em '{r_type}'. Valor original mantido.")
                                        r_value = retention.get('value', 'N/A') 
                                elif isinstance(r_value, str):
                                    # Para outros tipos, apenas limpa R$ e espaços e padroniza vírgula para decimal
                                    r_value = r_value.replace('R$', '').replace(' ', '').replace('.', ',').strip()

                                # --- FIM DA LÓGICA DE AJUSTE ---
                                
                                report_content.append(f"    - Tipo: {r_type}, Valor: {r_value}")
                        else:
                            report_content.append("    Nenhuma retenção encontrada.")
                        report_content.append("\n")
                    else:
                        report_content.append(f"--- Erro ao processar {pdf_file.filename} com a API Gemini ---")
                        report_content.append(f"Erro detalhado: Verifique os logs do servidor para mais informações.")
                        report_content.append("\n")
                else:
                    # Mensagem de erro para PDFs com pouco ou nenhum texto
                    report_content.append(f"--- Relatório para: {pdf_file.filename} ---")
                    report_content.append(f"Não foi possível extrair texto suficiente do arquivo '{pdf_file.filename}'.")
                    report_content.append("Por favor, verifique se o PDF contém texto legível ou se não é um PDF de imagem que precisa de OCR.")
                    report_content.append("\n")

            except Exception as e:
                logger.error(f"Erro inesperado ao processar o arquivo {pdf_file.filename}: {e}", exc_info=True)
                report_content.append(f"--- Erro ao processar {pdf_file.filename} ---")
                report_content.append(f"Ocorreu um erro inesperado: {str(e)}")
                report_content.append("\n")
            finally:
                pass 

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