from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import tempfile
import concurrent.futures
import io
import zipfile
import json
from pathlib import Path

# Importar as funções existentes
from .auxiliares.pdf_reader import validate_pdf, read_pdf
from .auxiliares.pdf_reader2 import read_pdf2
from .banco import get_processor
from .auxiliares.xml_to_csv import xml_to_csv

# Configurar o Flask com caminhos absolutos
base_dir = os.path.dirname(os.path.abspath(__file__))  # Obtém o caminho absoluto de extrator-contajur/
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, '../home/templates'),
            static_folder=os.path.join(base_dir, '../home/static'))
CORS(app)

# Configurações
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_pdf_content(file_content):
    """
    Valida se o conteúdo do arquivo é realmente um PDF
    """
    try:
        if file_content.startswith(b'%PDF-'):
            return True
        return False
    except Exception:
        return False

def process_single_pdf_flask(file_content, filename, bank, text):
    """
    Versão Flask da função process_single_pdf
    Processa um único PDF e retorna o resultado
    """
    try:
        if not text or not bank:
            return {
                'filename': filename,
                'success': False,
                'error': "❌ Arquivo inválido ou banco não identificado."
            }

        processor = get_processor(bank)
        result = processor(text)
        
        xml_data, txt_data = result
        
        if xml_data is None or txt_data is None:
            return {
                'filename': filename,
                'success': False,
                'error': "Nenhuma transação encontrada no arquivo."
            }
        
        xml_data.seek(0)
        csv_data = xml_to_csv(xml_data)
        
        return {
            'filename': filename,
            'success': True,
            'csv_data': csv_data,
            'error': None
        }

    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': f"❌ Erro no processamento: {str(e)}"
        }

def create_zip_from_results(results):
    """
    Cria um arquivo ZIP contendo todos os CSVs gerados
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for result in results:
            if result['success'] and result.get('csv_data'):
                csv_file_name = f"extrato_{result['filename'].rsplit('.', 1)[0]}.csv"
                csv_data = result['csv_data']
                if isinstance(csv_data, io.StringIO):
                    data = csv_data.getvalue().encode('utf-8')
                elif isinstance(csv_data, io.BytesIO):
                    data = csv_data.getvalue()
                else:
                    data = csv_data
                    if isinstance(data, str):
                        data = data.encode('utf-8')
                zip_file.writestr(csv_file_name, data)
    zip_buffer.seek(0)
    return zip_buffer

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({'status': 'OK', 'message': 'API está funcionando'})

@app.route('/api/process-extracts', methods=['POST'])
def process_extracts():
    """
    Endpoint principal para processar extratos bancários
    Recebe múltiplos PDFs e retorna os CSVs processados
    """
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'results': [],
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False,
                'results': [],
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        file_data = []
        for file in files:
            if file and file.filename != '':
                try:
                    if not allowed_file(file.filename):
                        file_data.append({
                            'filename': file.filename,
                            'bank': None,
                            'text': None,
                            'error': f"Arquivo '{file.filename}' não é um PDF válido (extensão)"
                        })
                        continue
                    
                    file_content = file.read()
                    if not validate_pdf_content(file_content):
                        file_data.append({
                            'filename': file.filename,
                            'bank': None,
                            'text': None,
                            'error': f"Arquivo '{file.filename}' não é um PDF válido (conteúdo)"
                        })
                        continue
                    
                    file.seek(0)
                    try:
                        text, identified_bank = read_pdf(file)
                        if identified_bank.startswith("Erro") or identified_bank == "Banco não identificado":
                            file_data.append({
                                'filename': file.filename,
                                'bank': None,
                                'text': None,
                                'error': f"Banco não identificado em '{file.filename}'"
                            })
                            continue
                    except Exception as pdf_error:
                        file_data.append({
                            'filename': file.filename,
                            'bank': None,
                            'text': None,
                            'error': f"Erro ao ler PDF '{file.filename}': {str(pdf_error)}"
                        })
                        continue
                    
                    if identified_bank in ['Bradesco', 'Sicoob1', 'Sicoob2', 'Sicoob3', 'Stone', 
                                         'Banco do Brasil1', 'Safra', 'Santander2', 'Efi1', 'Efi2', 'Mercado Pago']:
                        try:
                            file.seek(0)
                            text = read_pdf2(file)
                        except Exception as pdf2_error:
                            file_data.append({
                                'filename': file.filename,
                                'bank': None,
                                'text': None,
                                'error': f"Erro ao processar PDF '{file.filename}' com read_pdf2: {str(pdf2_error)}"
                            })
                            continue
                    
                    file_data.append({
                        'filename': file.filename,
                        'bank': identified_bank,
                        'text': text,
                        'error': None
                    })
                except Exception as e:
                    file_data.append({
                        'filename': file.filename,
                        'bank': None,
                        'text': None,
                        'error': f"Erro geral ao processar '{file.filename}': {str(e)}"
                    })
            else:
                file_data.append({
                    'filename': file.filename if file else 'Arquivo sem nome',
                    'bank': None,
                    'text': None,
                    'error': "Arquivo vazio ou inválido"
                })
        
        results = []
        valid_files = [f for f in file_data if f['bank'] is not None and f['text'] is not None]
        
        if valid_files:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_file = {
                    executor.submit(process_single_pdf_flask, None, file_info['filename'], file_info['bank'], file_info['text']):
                    file_info for file_info in valid_files
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append({
                            'filename': file_info['filename'],
                            'success': False,
                            'error': f"❌ Erro inesperado: {str(e)}"
                        })
        
        for file_info in file_data:
            if file_info['error']:
                results.append({
                    'filename': file_info['filename'],
                    'success': False,
                    'error': file_info['error']
                })
        
        successful_results = [r for r in results if r['success']]
        sanitized_results = [{'filename': r['filename'], 'success': r['success'], 'error': r['error']} for r in results]
        
        if successful_results:
            zip_buffer = create_zip_from_results(successful_results)
            temp_zip_path = os.path.join(UPLOAD_FOLDER, 'extratos_temp.zip')
            with open(temp_zip_path, 'wb') as f:
                f.write(zip_buffer.getvalue())
            return jsonify({
                'success': True,
                'message': f'{len(successful_results)} de {len(files)} arquivo(s) processado(s) com sucesso',
                'results': sanitized_results,
                'download_url': '/api/download-zip',
                'total_files': len(files),
                'successful_files': len(successful_results)
            })
        else:
            if len(files) == 1:
                # Simplifica para um único arquivo falho
                return jsonify({
                    'success': False,
                    'message': 'Processamento Concluído',
                    'results': [{'filename': files[0].filename, 'success': False, 'error': results[0]['error'] if results else 'Banco não identificado'}],
                    'total_files': len(files),
                    'successful_files': 0
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Nenhum arquivo foi processado com sucesso',
                    'results': sanitized_results,
                    'total_files': len(files),
                    'successful_files': 0
                }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'results': [],
            'error': f'Erro interno do servidor: {str(e)}'
        }), 500
        
@app.route('/api/download-zip', methods=['GET'])
def download_zip():
    """
    Endpoint para download do arquivo ZIP com os CSVs
    """
    try:
        temp_zip_path = os.path.join(UPLOAD_FOLDER, 'extratos_temp.zip')
        if not os.path.exists(temp_zip_path):
            return jsonify({'error': 'Arquivo ZIP não encontrado'}), 404
        return send_file(
            temp_zip_path,
            as_attachment=True,
            download_name='extratos.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({'error': f'Erro ao fazer download: {str(e)}'}), 500

@app.route('/api/identify-bank', methods=['POST'])
def identify_bank():
    """
    Endpoint para identificar apenas o banco de um PDF (útil para preview)
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'filename': file.filename,
                'bank': None,
                'error': 'Arquivo não é um PDF válido (extensão)'
            })
        file_content = file.read()
        if not validate_pdf_content(file_content):
            return jsonify({
                'success': False,
                'filename': file.filename,
                'bank': None,
                'error': 'Arquivo não é um PDF válido (conteúdo)'
            })
        file.seek(0)
        try:
            text, identified_bank = read_pdf(file)
            if identified_bank.startswith("Erro") or identified_bank == "Banco não identificado":
                return jsonify({
                    'success': False,
                    'filename': file.filename,
                    'bank': None,
                    'error': f"Banco não identificado: {identified_bank}"
                })
            return jsonify({
                'success': True,
                'filename': file.filename,
                'bank': identified_bank,
                'error': None
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'filename': file.filename,
                'bank': None,
                'error': f"Erro ao processar PDF: {str(e)}"
            })
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

@app.route('/api/debug-file', methods=['POST'])
def debug_file():
    """
    Endpoint para debug - verificar informações detalhadas do arquivo
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        file_info = {
            'filename': file.filename,
            'content_type': file.content_type,
            'size': 0,
            'extension_valid': allowed_file(file.filename),
            'pdf_signature': False,
            'first_bytes': '',
            'error': None
        }
        try:
            file_content = file.read()
            file_info['size'] = len(file_content)
            if file_content.startswith(b'%PDF-'):
                file_info['pdf_signature'] = True
            file_info['first_bytes'] = file_content[:20].hex() if file_content else ''
            file.seek(0)
            try:
                text, identified_bank = read_pdf(file)
                file_info['read_pdf_success'] = True
                file_info['identified_bank'] = identified_bank
                file_info['text_length'] = len(text) if text else 0
            except Exception as read_error:
                file_info['read_pdf_success'] = False
                file_info['read_pdf_error'] = str(read_error)
        except Exception as e:
            file_info['error'] = str(e)
        return jsonify(file_info)
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

@app.route('/')
def index():
    """Rota principal - renderiza o home.html"""
    return render_template('home.html')

@app.route('/extrator')
def extrator():
    """Rota para renderizar o extrator.html"""
    return render_template('extrator.html')
