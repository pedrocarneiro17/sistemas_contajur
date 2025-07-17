import os
from flask import Blueprint, request, send_file, render_template
import requests
import json
import pdfplumber
import tempfile
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

retencao_bp = Blueprint('retencao_notas', __name__, url_prefix='/retencao_notas',
                        template_folder='templates', static_folder='static')

GEMINI_API_KEY = "AIzaSyA0hJdqhpW0cyaZ6K_ezA82lTMJWOiRO44"
TEXT_MIN_LENGTH_FOR_NATIVE_PDF = 300

def extract_text_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        cleaned_text = text.strip()
        logger.info(f"Extração com pdfplumber concluída para: {pdf_path}. Caracteres: {len(cleaned_text)}")
        return cleaned_text
    except Exception as e:
        logger.error(f"Erro ao extrair texto com pdfplumber de {pdf_path}: {e}")
        return None

def process_pdf_with_gemini(pdf_text):
    if not pdf_text:
        logger.warning("Nenhum texto fornecido para a API Gemini.")
        return None

    prompt = (
        "Analise o texto de nota fiscal em português e extraia:\n"
        "1. Nome da empresa (preferencialmente o Prestador de Serviços).\n"
        "2. Lista de retenções com valores, incluindo 'Retenções Federais', 'ISS Retido na Fonte', 'Valor do ISS', 'Valor do ISS Devido (R$)', 'Valor Retido IR', 'INSS', 'CSLL', 'IR', 'IRRF', 'COFINS', 'PIS/PASEP', 'Outras retenções'.\n"
        "3. Valores podem estar na mesma linha ou na linha seguinte (ex.: 'Valor do ISS Devido (R$)' seguido por '120,67').\n"
        "4. Inclua 'Valor do ISS Devido (R$)' como retenção se 'Valor do ISS Retido (R$)' for 0 ou ausente.\n"
        "5. Se houver 'Base de Cálculo de ISSQN' e 'Valor do ISS' ou 'Valor do ISS Devido (R$)', subtraia o valor de ISS da Base de Cálculo e inclua como 'Base de Cálculo de ISSQN' se maior que 0.\n"
        "6. Se o valor de uma retenção for 0,00 não inclua ela na lista.\n"
        "7. Caso identifique '-', considere como um valor, que é 0 no caso.\n"
        "8. Remova prefixos como 'R$' ou '(R$)' dos valores, mantendo o formato original (ex.: '123,45').\n"
        "9. Se não houver retenções, retorne 'Nenhuma retenção encontrada'.\n"
        "10. Não invente valores ou retenções.\n"
        f"Texto da Nota Fiscal:\n{pdf_text}"
    )

    chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
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
                            "required": ["type", "value"]
                        }
                    }
                },
                "required": ["company_name", "retentions"]
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
    except (requests.exceptions.RequestException, json.JSONDecodeError, Exception) as e:
        logger.error(f"Erro ao processar com Gemini: {e}")
        return None

@retencao_bp.route('/')
def retencao_notas_page():
    return render_template('retencao_notas.html')

@retencao_bp.route('/upload', methods=['POST'])
def upload_pdfs():
    if 'pdfs' not in request.files:
        logger.error("Nenhum arquivo 'pdfs' fornecido.")
        return "Erro: Nenhum arquivo 'pdfs' fornecido.", 400

    uploaded_files = request.files.getlist('pdfs')
    if not uploaded_files:
        logger.error("Nenhum arquivo selecionado para upload.")
        return "Erro: Nenhum arquivo selecionado.", 400

    report_content = []
    temp_files_to_clean = []

    try:
        for pdf_file in uploaded_files:
            if pdf_file.filename == '':
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(pdf_file.read())
                tmp_pdf_path = tmp_pdf.name
                temp_files_to_clean.append(tmp_pdf_path)
                logger.info(f"Arquivo PDF '{pdf_file.filename}' salvo temporariamente como: {tmp_pdf_path}")

            pdf_text = extract_text_from_pdf(tmp_pdf_path)
            
            if pdf_text and len(pdf_text) >= TEXT_MIN_LENGTH_FOR_NATIVE_PDF:
                logger.info(f"Texto suficiente ({len(pdf_text)} caracteres) extraído para {pdf_file.filename}.")
                extracted_data = process_pdf_with_gemini(pdf_text)
                if extracted_data:
                    report_content.append(f"--- Relatório para: {pdf_file.filename} ---")
                    report_content.append(f"Nome da Empresa: {extracted_data.get('company_name', 'Não encontrado')}")
                    report_content.append("Retenções:")
                    if extracted_data.get('retentions'):
                        for retention in extracted_data['retentions']:
                            r_type = retention.get('type', 'N/A')
                            r_value = retention.get('value', 'N/A')
                            report_content.append(f"    - Tipo: {r_type}, Valor: {r_value}")
                    else:
                        report_content.append("    Nenhuma retenção encontrada.")
                    report_content.append("\n")
                else:
                    report_content.append(f"--- Erro ao processar {pdf_file.filename} com a API Gemini ---")
                    report_content.append("Erro: Verifique os logs do servidor.")
                    report_content.append("\n")
            else:
                report_content.append(f"--- Relatório para: {pdf_file.filename} ---")
                report_content.append(f"Não foi possível extrair texto suficiente de '{pdf_file.filename}'.")
                report_content.append("Verifique se o PDF contém texto legível.")
                report_content.append("\n")

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