"""
Utilitários para certificado digital eCNPJ (.pfx / .p12).

Certificados brasileiros frequentemente usam cifras legadas (RC2, 3DES, SHA1).
A abordagem mais confiável é usar o openssl CLI ou requests-pkcs12 diretamente.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def carregar_pfx_bytes(pfx_path: str | Path) -> bytes:
    with open(pfx_path, "rb") as f:
        return f.read()


def montar_sessao_com_certificado(session, pfx_path: str | Path, senha: str) -> bool:
    """
    Configura a sessão requests com o certificado PKCS12.
    Tenta requests-pkcs12 primeiro (mais confiável para certs legados BR).
    Retorna True se conseguiu montar.
    """
    senha_bytes = senha.encode() if isinstance(senha, str) else senha
    pfx_data = carregar_pfx_bytes(pfx_path)

    # --- Opção 1: requests-pkcs12 adapter ---
    try:
        from requests_pkcs12 import Pkcs12Adapter
        adapter = Pkcs12Adapter(pkcs12_data=pfx_data, pkcs12_password=senha_bytes)
        session.mount("https://", adapter)
        logger.info("Certificado montado via requests-pkcs12")
        return True
    except Exception as e:
        logger.warning("requests-pkcs12 falhou: %s", e)

    # --- Opção 2: converte PFX→PEM via openssl CLI ---
    try:
        cert_pem, key_pem = pfx_para_pem_via_openssl(pfx_path, senha)
        cert_file = tempfile.NamedTemporaryFile(suffix="_cert.pem", delete=False)
        key_file  = tempfile.NamedTemporaryFile(suffix="_key.pem",  delete=False)
        cert_file.write(cert_pem); cert_file.flush()
        key_file.write(key_pem);   key_file.flush()
        session.cert = (cert_file.name, key_file.name)
        # Guarda caminhos para limpeza posterior
        session._gnre_pem_cert = cert_file.name
        session._gnre_pem_key  = key_file.name
        logger.info("Certificado montado via openssl CLI (PEM temporário)")
        return True
    except Exception as e:
        logger.warning("openssl CLI falhou: %s", e)

    return False


def pfx_para_pem_via_openssl(pfx_path: str | Path, senha: str) -> tuple[bytes, bytes]:
    """
    Usa o binário `openssl` instalado no sistema para converter PFX→PEM.
    Compatível com qualquer cifra, incluindo RC2 e 3DES legados.
    """
    openssl_bin = _localizar_openssl()
    pfx_path    = str(pfx_path)

    tmp_cert = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    tmp_key  = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    tmp_cert.close(); tmp_key.close()

    try:
        # Extrai certificado público
        _run_openssl(openssl_bin, [
            "pkcs12", "-in", pfx_path,
            "-nokeys", "-out", tmp_cert.name,
            "-passin", f"pass:{senha}",
            "-legacy",                          # suporte a certs antigos
        ])

        # Extrai chave privada sem senha
        _run_openssl(openssl_bin, [
            "pkcs12", "-in", pfx_path,
            "-nocerts", "-nodes",
            "-out", tmp_key.name,
            "-passin", f"pass:{senha}",
            "-legacy",
        ])

        cert_pem = Path(tmp_cert.name).read_bytes()
        key_pem  = Path(tmp_key.name).read_bytes()
        return cert_pem, key_pem

    finally:
        for p in (tmp_cert.name, tmp_key.name):
            try: os.unlink(p)
            except Exception: pass


def _run_openssl(bin_path: str, args: list[str]) -> None:
    r = subprocess.run(
        [bin_path] + args,
        capture_output=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace"))


def _localizar_openssl() -> str:
    """Localiza o binário openssl no sistema. Levanta FileNotFoundError se não achar."""
    # 1. Verifica se está no PATH
    if shutil.which("openssl"):
        return "openssl"

    # 2. Locais comuns no Windows
    candidatos = [
        r"C:\Program Files\Git\usr\bin\openssl.exe",
        r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
        r"C:\Program Files\OpenSSL\bin\openssl.exe",
        r"C:\Program Files (x86)\Git\usr\bin\openssl.exe",
        r"C:\Windows\System32\openssl.exe",
    ]
    for caminho in candidatos:
        if Path(caminho).exists():
            return caminho

    raise FileNotFoundError(
        "openssl não encontrado no sistema.\n"
        "Instale o Git para Windows (https://git-scm.com) ou o OpenSSL para Windows.\n"
        "O openssl vem incluído no Git for Windows."
    )


def limpar_pem_temporarios(cert_pem: str | None, key_pem: str | None) -> None:
    for path in (cert_pem, key_pem):
        if path:
            try: Path(path).unlink(missing_ok=True)
            except Exception: pass
