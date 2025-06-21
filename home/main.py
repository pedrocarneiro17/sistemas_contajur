import os
import sys

# Garante que o diretório pai (que contém extrator_contajur) esteja no sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extrator_contajur import app  # Importa o app definido em app.py

if __name__ == '__main__':
    app.run()
