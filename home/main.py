import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from extrator_contajur import app  # Importa o app definido em app.py

if __name__ == '__main__':
    app.run(debug=False)  # Remova host e port, pois o Vercel gerencia isso