from flask import Blueprint, request, jsonify, render_template, send_file
import os
import tempfile
from .utils.pdf_reader import read_pdf_and_identify_model
from .processadores.bling_processor import process_bling_pdf
from .processadores.sgbr_processor import process_sgbr_pdf
from .processadores.fechamento_processor import process_fechamento_pdf
from .processadores.totais_processor import process_totais_pdf
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
    Converte um valor para float de forma segura, tratando None, números e strings com vírgula ou ponto.
    Suporta formatos brasileiros (1.234,56) e US (1,234.56 ou 12.0).
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        value = value.replace(' ', '')
        try:
            return float(value)
        except (ValueError, TypeError):
            try:
                br_value = value.replace('.', '').replace(',', '.')
                return float(br_value)
            except (ValueError, TypeError):
                return None
                
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

        # Identificar duplicatas com datas diferentes
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
        elif modelo == 'Relatório Totais':
            pdf_df, pdf_missing_nums, pdf_compare_df = process_totais_pdf(texto_completo)
            id_col_pdf, val_col_pdf = 'Número', 'V.NF'
        else:
            raise ValueError(f"Modelo de PDF '{modelo}' não suportado.")

        # --- 3. Verificação de Valores ---
        id_col_excel, val_col_excel = 'Nr. documento', 'Valor da nota' 
        
        comparison_report = []
        if val_col_excel in excel_df.columns:
            excel_df_compare = excel_df[[id_col_excel, val_col_excel]].copy()
            # Agrupa valores do Excel por ID para lidar com duplicatas
            excel_lookup = excel_df_compare.groupby(id_col_excel)[val_col_excel].apply(list).to_dict()

            divergencias = 0
            problemas_duplicatas = 0
            for _, row in pdf_compare_df.iterrows():
                try:
                    doc_id = int(row[id_col_pdf])
                except (ValueError, TypeError):
                    continue 

                pdf_val = safe_to_float(row[val_col_pdf])
                
                if doc_id not in excel_lookup:
                    # CORRIGIDO: avaliar condição antes de formatar
                    pdf_val_formatted = f'{pdf_val:.2f}' if pdf_val is not None else 'N/A'
                    comparison_report.append(
                        f"  - ID {doc_id}: Encontrado no PDF (R$ {pdf_val_formatted}), mas ausente no Excel.".replace('.', ',')
                    )
                    continue

                excel_vals = [safe_to_float(val) for val in excel_lookup[doc_id]]
                if len(excel_vals) > 1:
                    problemas_duplicatas += 1
                    excel_vals_str = ', '.join([f'R$ {ev:.2f}' for ev in excel_vals if ev is not None]).replace('.', ',')
                    # CORRIGIDO: avaliar condição antes de formatar
                    pdf_val_formatted = f'{pdf_val:.2f}' if pdf_val is not None else 'N/A'
                    pdf_val_str = f'R$ {pdf_val_formatted}'.replace('.', ',') if pdf_val is not None else 'N/A'
                    comparison_report.append(
                        f"  - ID {doc_id}: Múltiplos valores no Excel ({excel_vals_str}). Valor no PDF: {pdf_val_str}."
                    )
                elif len(excel_vals) == 1:
                    excel_val = excel_vals[0]
                    if pdf_val is not None and excel_val is not None:
                        if not np.isclose(pdf_val, excel_val, atol=0.01):
                            divergencias += 1
                            comparison_report.append(
                                f"  - ID {doc_id}: Divergência de valores -> PDF: R$ {pdf_val:.2f} | Excel: R$ {excel_val:.2f}".replace('.', ',')
                            )
                    else:
                        # CORRIGIDO: avaliar condição antes de formatar
                        pdf_val_str = f'R$ {pdf_val:.2f}'.replace('.', ',') if pdf_val is not None else 'N/A'
                        excel_val_str = f'R$ {excel_val:.2f}'.replace('.', ',') if excel_val is not None else 'N/A'
                        comparison_report.append(
                            f"  - ID {doc_id}: Valor inválido -> PDF: {pdf_val_str} | Excel: {excel_val_str}."
                        )
                else:
                    comparison_report.append(f"  - ID {doc_id}: Nenhum valor válido encontrado no Excel.")

            # Verificar duplicatas no PDF
            duplicatas_pdf = pdf_compare_df[pdf_compare_df[id_col_pdf].duplicated(keep=False)][id_col_pdf].unique()
            comparison_summary = (
                f"Verificação concluída. {len(pdf_compare_df)} documentos analisados.\n"
                f"  - Divergências de valor: {divergencias}\n"
                f"  - IDs com múltiplos valores no Excel: {problemas_duplicatas}\n"
                f"  - IDs duplicados no PDF: {len(duplicatas_pdf)}"
            )
        else:
            comparison_summary = f"AVISO: Não foi possível verificar valores, pois a coluna '{val_col_excel}' não foi encontrada no Excel."

        # --- 4. Geração do Relatório .txt Completo ---
        report_content = [
            f"Relatório de Processamento - Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "="*50,
            "\n--- Verificação de Valores (PDF vs. Excel) ---",
            comparison_summary
        ]
        if comparison_report:
            report_content.append("\nDetalhes:")
            report_content.extend(comparison_report)
        
        if duplicatas_pdf.size > 0:
            report_content.extend([
                "\n--- IDs Duplicados no PDF ---",
                f"Total: {len(duplicatas_pdf)}",
                "IDs: " + ", ".join(map(str, sorted(duplicatas_pdf)))
            ])

        report_content.extend(["\n--- Análise da Planilha Excel ---"])
        report_content.append(f"Total de duplicatas exatas (mesmo número e chave) removidas: {len(excel_duplicates_removed)}")
        if excel_duplicates_removed:
            report_content.append("Documentos removidos: " + ", ".join(map(str, excel_duplicates_removed)))
        
        report_content.extend(["\n--- Notas duplicadas com chaves diferentes (mantidas na planilha) ---"])
        if notas_duplicadas_datas_diferentes:
            report_content.append(f"Total de notas encontradas: {len(notas_duplicadas_datas_diferentes)}")
            report_content.append("Números das notas: " + ", ".join(map(str, sorted(notas_duplicadas_datas_diferentes))))
        else:
            report_content.append("Nenhuma nota com número duplicado e chave diferente foi encontrada.")
        
        report_content.extend([
            "\n--- Análise do Arquivo PDF ---",
            f"Modelo Identificado: {modelo}",
            f"Total de números faltantes adicionados: {len(pdf_missing_nums)}"
        ])
        if pdf_missing_nums:
            report_content.append("Números adicionados: " + ", ".join(map(str, pdf_missing_nums)))
        
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