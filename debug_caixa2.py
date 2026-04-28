"""
Roda no terminal: python debug_caixa2.py caminho/para/caixa2.pdf
"""
import sys
import os
import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extrator_contajur.banco.caixa2 import preprocess_text

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else input("Caminho do PDF: ").strip()

    # 1. Extrair texto com PyMuPDF
    print("\n" + "="*60)
    print("TEXTO BRUTO (PyMuPDF) — primeiras 100 linhas")
    print("="*60)
    doc = fitz.open(path)
    raw = ""
    for page in doc:
        raw += page.get_text() + "\n"
    doc.close()

    lines = raw.splitlines()
    for i, line in enumerate(lines[:100], 1):
        print(f"{i:>3}: {repr(line)}")

    # 2. Rodar o parser
    print("\n" + "="*60)
    print("RESULTADO DO PARSER")
    print("="*60)
    transacoes = preprocess_text(raw)

    if not transacoes:
        print("⚠️  Nenhuma transação encontrada.")
    else:
        print(f"✅  {len(transacoes)} transação(ões) encontrada(s):\n")
        for t in transacoes:
            print(f"  Data: {t['Data']}  Tipo: {t['Tipo']}  Valor: {t['Valor']}")
            print(f"  Desc: {t['Descrição']}")
            print()

if __name__ == "__main__":
    main()
