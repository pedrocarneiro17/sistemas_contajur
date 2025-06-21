import os
import sys

# Garante que o diretório pai (que contém extrator_contajur) esteja no sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extrator_contajur import app  # Importa o app definido em app.py

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Rodando na porta {port}")  # <-- Aqui o print
    app.run(host="0.0.0.0", port=port)
