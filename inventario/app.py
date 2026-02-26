import os
import pandas as pd
import pdfplumber
import zipfile
from flask import Blueprint, render_template, request, send_file
from io import BytesIO

# Importação dos modelos
from inventario.models.gestao_estoque import GestaoEstoque
from inventario.models.modelo_brasart import ModeloBrasArt
from inventario.models.modelo_listagem_simples import ModeloListagemSimples
from inventario.models.modelo_p7 import ModeloP7
from inventario.models.modelo_p7_2 import ModeloP72
from inventario.models.modelo_p7_3 import ModeloP73
from inventario.models.modelo_registro_inventario import ModeloRI
from inventario.models.posicao_estoque import PosicaoEstoque

inventario_bp = Blueprint('inventario', __name__)

def identificar_modelo(primeira_pagina_texto):
    if "LIVRO REGISTRO DE INVENTÁRIO - RI - MODELO P7" in primeira_pagina_texto:
        return ModeloP7
    elif "Livro Registro de Inventário - RI - Modelo P7" in primeira_pagina_texto:
        return ModeloP72
    elif "Listagem Simples dos Produtos do Inventário" in primeira_pagina_texto:
        return ModeloListagemSimples
    elif "REGISTRO DE INVENTÁRIO - MODELO P7" in primeira_pagina_texto:
        return ModeloP73
    elif "REGISTRO DE INVENTÁRIO" in primeira_pagina_texto:
        return ModeloRI
    elif "Posição de Estoque" in primeira_pagina_texto:
         return PosicaoEstoque
    elif "Preco venda Custo" in primeira_pagina_texto:
         return ModeloBrasArt
    elif "Gestão de Estoque" in primeira_pagina_texto:
         return GestaoEstoque
    return None

@inventario_bp.route('/inventario')
def inventario_page():
    return render_template('inventario.html')

@inventario_bp.route('/inventario/upload', methods=['POST'])
def upload():
    files = request.files.getlist('inventarios')
    if not files:
        return "Nenhum arquivo enviado", 400

    # Buffer para o arquivo final (pode ser CSV ou ZIP)
    memory_file = BytesIO()

    if len(files) == 1:
        # --- PROCESSO PARA ARQUIVO ÚNICO (Retorna .csv) ---
        file = files[0]
        nome_csv = os.path.splitext(file.filename)[0] + ".csv"
        
        texto_pdf = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                texto_pdf += (page.extract_text() or "") + "\n"
        
        ModelClass = identificar_modelo(texto_pdf)
        if not ModelClass:
            return f"Modelo não identificado para o arquivo: {file.filename}", 422
            
        dados = ModelClass(texto_pdf).process()
        df = pd.DataFrame(dados)
        df.to_csv(memory_file, index=False, sep=';', encoding='utf-8-sig')
        memory_file.seek(0)
        
        return send_file(memory_file, mimetype='text/csv', as_attachment=True, download_name=nome_csv)

    else:
        # --- PROCESSO PARA MÚLTIPLOS ARQUIVOS (Retorna .zip) ---
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                texto_pdf = ""
                try:
                    with pdfplumber.open(file) as pdf:
                        for page in pdf.pages:
                            texto_pdf += (page.extract_text() or "") + "\n"
                    
                    ModelClass = identificar_modelo(texto_pdf)
                    if ModelClass:
                        dados = ModelClass(texto_pdf).process()
                        df = pd.DataFrame(dados)
                        
                        # Converte DF para CSV em string para colocar no ZIP
                        csv_buffer = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
                        nome_csv = os.path.splitext(file.filename)[0] + ".csv"
                        zf.writestr(nome_csv, csv_buffer)
                except Exception as e:
                    print(f"Erro ao processar {file.filename}: {e}")

        memory_file.seek(0)
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='inventarios_processados.zip')