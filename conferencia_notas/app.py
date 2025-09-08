from flask import Blueprint, request, jsonify, render_template, send_file
import os
import tempfile
from .utils.pdf_reader import read_pdf_and_identify_model
from .processadores.bling_processor import process_bling_pdf
from .processadores.sgbr_processor import process_sgbr_pdf
from .processadores.fechamento_processor import process_fechamento_pdf
from .utils.excel_processor import remove_duplicatas_e_vazias_xls
import io
import logging
import zipfile
from datetime import datetime
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
conferencia_bp = Blueprint('conferencia', __name__)

def safe_to_float(value):
    """
    Converte um valor para float de forma segura, tratando None, números e strings com vírgula.
    """
    # CORREÇÃO: Se o valor já for um número (int ou float), retorna-o diretamente.
    # Isso evita a conversão incorreta de valores numéricos vindos do Excel.
    if isinstance(value, (int, float)):
        return float(value)
    
    # Se for uma string, processa para remover separadores e ajustar o decimal.
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            # Esta lógica funciona para formatos como "1.234,56" ou "23,00"
            return float(value.replace('.', '').replace(',', '.'))
        except (ValueError, TypeError):
            return None
            
    # Se não for um tipo esperado, retorna None.
    return None

@conferencia_bp.route('/conferencia')
def conferencia():
    return render_template('conferencia.html')

@conferencia_bp.route('/api/process-all', methods=['POST'])
def process_all():
    tmp_pdf_path = None
    try:
        if 'pdf' not in request.files or 'excel' not in request.files:
            return jsonify({'success': False, 'error': 'É necessário enviar um arquivo PDF e um Excel.'}), 400
        pdf_file, excel_file = request.files['pdf'], request.files['excel']

        # --- 1. Processamento do Excel ---
        excel_df, excel_duplicates_removed = remove_duplicatas_e_vazias_xls(excel_file)

        # --- [NOVA ANÁLISE] Identificar duplicatas com datas diferentes ---
        # Após a remoção de duplicatas exatas, contamos as ocorrências restantes de cada 'Nr. documento'.
        # Se um número ainda aparece mais de uma vez, é porque as datas são distintas.
        counts = excel_df['Nr. documento'].value_counts()
        notas_duplicadas_datas_diferentes = counts[counts > 1].index.tolist()


        # --- 2. Processamento do PDF ---
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.read())
            tmp_pdf_path = tmp.name
        
        modelo, texto_completo = read_pdf_and_identify_model(tmp_pdf_path)
        
        if modelo == 'Bling':
            pdf_df, pdf_missing_nums, pdf_compare_df = process_bling_pdf(texto_completo)
            id_col_pdf, val_col_pdf = 'Número', 'Valor'
        elif modelo == 'SGBr Sistemas':
            pdf_df, pdf_missing_nums, pdf_compare_df = process_sgbr_pdf(texto_completo)
            id_col_pdf, val_col_pdf = 'Número', 'Total nota'
        elif modelo == 'Relatório Fechamento Fiscal Entradas':
            pdf_df, pdf_missing_nums, pdf_compare_df = process_fechamento_pdf(texto_completo)
            id_col_pdf, val_col_pdf = 'N° NF', 'Total NF'
        else:
            raise ValueError(f"Modelo de PDF '{modelo}' não suportado.")

        # --- 3. Verificação de Valores ---
        id_col_excel, val_col_excel = 'Nr. documento', 'Valor da nota' 
        
        comparison_report = []
        if val_col_excel in excel_df.columns:
            excel_df_compare = excel_df[[id_col_excel, val_col_excel]].copy()
            excel_lookup = excel_df_compare.set_index(id_col_excel)[val_col_excel]

            divergencias = 0
            for _, row in pdf_compare_df.iterrows():
                try:
                    doc_id = int(row[id_col_pdf])
                except (ValueError, TypeError):
                    continue 

                pdf_val = safe_to_float(row[val_col_pdf])
                
                if doc_id in excel_lookup.index:
                    excel_val = safe_to_float(excel_lookup[doc_id])
                    
                    if pdf_val is not None and excel_val is not None:
                        if not np.isclose(pdf_val, excel_val, atol=0.01):
                            divergencias += 1
                            comparison_report.append(f"  - ID {doc_id}: Divergência -> PDF R$ {pdf_val:.2f} vs Excel R$ {excel_val:.2f}".replace('.',','))
                    else:
                        comparison_report.append(f"  - ID {doc_id}: Um dos valores não pôde ser lido (PDF: {row[val_col_pdf]}, Excel: {excel_lookup.get(doc_id)}).")
                else:
                    comparison_report.append(f"  - ID {doc_id}: Encontrado no PDF, mas não na planilha Excel.")
            
            comparison_summary = f"Verificação concluída. {len(pdf_compare_df)} documentos checados. Encontradas {divergencias} divergências de valor."
        else:
            comparison_summary = f"AVISO: Não foi possível fazer a verificação de valores, pois a coluna '{val_col_excel}' não foi encontrada na planilha."
            
        # --- 4. Geração do Relatório .txt Completo ---
        report_content = [f"Relatório de Processamento - Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "="*50]
        report_content.extend(["\n--- Verificação de Valores (PDF vs. Excel) ---", comparison_summary])
        if comparison_report: report_content.extend(comparison_report)
        
        report_content.extend(["\n--- Análise da Planilha Excel ---"])
        # Seção de duplicatas exatas removidas
        report_content.append(f"Total de duplicatas exatas (mesmo número e chave) removidas: {len(excel_duplicates_removed)}")
        if excel_duplicates_removed: report_content.append("Documentos removidos: " + ", ".join(map(str, excel_duplicates_removed)))
        
        # --- [NOVA SEÇÃO NO RELATÓRIO] ---
        report_content.extend(["\n--- Notas duplicadas com chaves diferentes (mantidas na planilha) ---"])
        if notas_duplicadas_datas_diferentes:
            report_content.append(f"Total de notas encontradas: {len(notas_duplicadas_datas_diferentes)}")
            report_content.append("Números das notas: " + ", ".join(map(str, sorted(notas_duplicadas_datas_diferentes))))
        else:
            report_content.append("Nenhuma nota com número duplicado e chave diferente foi encontrada.")
        
        report_content.extend(["\n--- Análise do Arquivo PDF ---", f"Modelo Identificado: {modelo}", f"Total de números faltantes adicionados: {len(pdf_missing_nums)}"])
        if pdf_missing_nums: report_content.append("Números adicionados: " + ", ".join(map(str, pdf_missing_nums)))
        
        final_report = "\n".join(report_content)

        # --- 5. Criação do Arquivo ZIP ---
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            with io.BytesIO() as excel_buffer:
                excel_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                zip_file.writestr('resultado_da_planilha.xlsx', excel_buffer.getvalue())
            with io.BytesIO() as pdf_buffer:
                pdf_df.to_excel(pdf_buffer, index=False, engine='openpyxl')
                zip_file.writestr('resultado_do_pdf.xlsx', pdf_buffer.getvalue())
            
            zip_file.writestr('relatorio_processamento.txt', final_report.encode('utf-8'))
        
        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name='arquivos_processados.zip', mimetype='application/zip')

    except Exception as e:
        logger.error(f"Erro no processamento unificado: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro ao processar os arquivos: {str(e)}'}), 500
    finally:
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            os.unlink(tmp_pdf_path)