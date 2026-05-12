import io
from flask import Blueprint, request, send_file, render_template, jsonify
from flask_cors import CORS

from extrator_contajur.auxiliares.pdf_reader import read_pdf
from extrator_contajur.auxiliares.pdf_reader2 import read_pdf2
from extrator_contajur.banco import get_processor
from extrator_contajur.auxiliares.xml_to_csv import xml_to_csv
from .processador import processar

extrator_d_bp = Blueprint("extrator_d", __name__, url_prefix="/extrator-d")
CORS(extrator_d_bp)

BANKS_USING_PDF2 = {
    'Asaas', 'Bradesco', 'Sicoob1', 'Sicoob2', 'Sicoob3', 'Stone', 'Sicredi', 'Itaú4',
    'Banco do Brasil1', 'Safra', 'Santander2', 'Efi1', 'Efi2', 'Mercado Pago', 'Caixa2'
}


def _pdf_to_csv_bytes(file) -> tuple[bytes, str]:
    """Converte PDF de extrato em bytes CSV. Retorna (csv_bytes, banco)."""
    text, bank = read_pdf(file)
    if not text or bank.startswith("Erro") or bank == "Banco não identificado":
        raise ValueError(f"Banco não identificado: {bank}")

    if bank in BANKS_USING_PDF2:
        file.seek(0)
        text = read_pdf2(file)

    processor = get_processor(bank)
    xml_data, _ = processor(text)
    if xml_data is None:
        raise ValueError("Nenhuma transação encontrada no PDF.")

    xml_data.seek(0)
    csv_data = xml_to_csv(xml_data)

    if isinstance(csv_data, io.StringIO):
        csv_bytes = csv_data.getvalue().encode("utf-8")
    elif isinstance(csv_data, io.BytesIO):
        csv_bytes = csv_data.getvalue()
    else:
        csv_bytes = csv_data if isinstance(csv_data, bytes) else csv_data.encode("utf-8")

    return csv_bytes, bank


@extrator_d_bp.route("/")
def index():
    return render_template("extrator_d.html")


@extrator_d_bp.route("/upload", methods=["POST"])
def upload():
    """
    Form-data:
        files[]: um ou mais PDFs de extrato bancário
        nome[]:  lista de nomes para busca
        cpf[]:   lista de CPFs/6 dígitos para busca (mesma ordem dos nomes)
    """
    files = request.files.getlist("files[]")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"success": False, "error": "Nenhum arquivo enviado (campo: files[])"}), 400

    nomes = request.form.getlist("nome[]")
    cpfs  = request.form.getlist("cpf[]")

    max_len = max(len(nomes), len(cpfs), 1)
    nomes += [""] * (max_len - len(nomes))
    cpfs  += [""] * (max_len - len(cpfs))

    buscas = [{"nome": n, "cpf": c} for n, c in zip(nomes, cpfs) if n.strip() or c.strip()]

    try:
        csv_parts = []
        erros = []
        for file in files:
            if not file or file.filename == "":
                continue
            if not file.filename.lower().endswith(".pdf"):
                erros.append(f"{file.filename}: não é PDF")
                continue
            try:
                csv_bytes, _ = _pdf_to_csv_bytes(file)
                csv_parts.append(csv_bytes)
            except ValueError as e:
                erros.append(f"{file.filename}: {e}")

        if not csv_parts:
            msg = "; ".join(erros) if erros else "Nenhum arquivo processado com sucesso"
            return jsonify({"success": False, "error": msg}), 422

        # Concatena todos os CSVs (um após o outro, sem cabeçalho)
        combined_csv = b"\n".join(p.rstrip(b"\n") for p in csv_parts)

        excel = processar(combined_csv, buscas)

        nome_arquivo = "debitos.xlsx" if len(csv_parts) > 1 else (
            files[0].filename.rsplit(".", 1)[0] + "_debitos.xlsx"
        )
        return send_file(
            excel,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro interno: {e}"}), 500
