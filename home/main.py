import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extrator_contajur import app  # Importa o app Flask do módulo extrator_contajur

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)