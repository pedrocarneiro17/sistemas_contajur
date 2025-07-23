import os
import sys
from flask import Flask, render_template
from flask_cors import CORS

# Adiciona o diretório pai ao sys.path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar Blueprints
from extrator_contajur.app import extrator_bp
from conferencia_notas.app import conferencia_bp
from boletos.app import boletos_bp
from retencao_notas.app import retencao_bp

# Configurar o Flask
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
CORS(app)

# Configurações
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Registrar Blueprints
app.register_blueprint(extrator_bp)
app.register_blueprint(conferencia_bp)
app.register_blueprint(boletos_bp) 
app.register_blueprint(retencao_bp)

# Rota principal
@app.route('/')
def index():
    """Rota principal - renderiza o home.html"""
    return render_template('home.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Rodando na porta {port}")
    app.run(host="0.0.0.0", port=port)