import re
from ..auxiliares.utils import process_transactions  

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Itaú3 (AM AUTO PECAS ACESS LTDA ME) para extrair transações.
    Ignora cabeçalho, rodapé, saldos, notas explicativas e totalizadores.
    Formata datas como DD/MM/YYYY, valores como X.XXX,XX, e identifica tipo (C para crédito, D para débito).
    Para a captura ao encontrar "Saldo final" ou "Saldo em C/C", ignorando essas linhas.
    Mantém todas as transações, mesmo as repetidas.
    """
    # Normalizar texto: remover espaços extras e caracteres especiais
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Padrões regex
    date_pattern = re.compile(r"^\d{2}/\d{2}\s+.*?(?:\s+\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:-)?)?(?:\s+\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:-)?)?(?:\s+\d{1,3}(?:\.\d{3})*(?:,\d{2})?)?$", re.MULTILINE)
    value_pattern = re.compile(r"^(?!\d{2}/\d{2}\s+).*?(?:\s+\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:-)?)(?:\s+\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:-)?)?$", re.MULTILINE)
    year_pattern = re.compile(r"extrato mensal.*?(\d{4})\s+\d{3}\|\d{3}", re.IGNORECASE)
    prefix_pattern = re.compile(r"^(.*?=\s*poupança automática\s+)(.*?)$", re.IGNORECASE)
    saldo_final_pattern = re.compile(r"Saldo final", re.IGNORECASE)
    saldo_aplic_pattern = re.compile(r"SALDO APLIC AUT MAIS", re.IGNORECASE)
    saldo_cc_pattern = re.compile(r"Saldo em C/C", re.IGNORECASE)
    monetary_pattern = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}))(?:-)?")  # Captura primeiro valor monetário

    transactions = []
    current_date = None
    year = None
    capture_transactions = False
    
    for line in lines:
        # Extrair ano do cabeçalho
        if not year:
            year_match = year_pattern.search(line)
            if year_match:
                year = year_match.group(1)
                continue

        # Para de capturar transações se encontrar "Saldo final" ou "Saldo em C/C"
        if saldo_final_pattern.search(line) or saldo_cc_pattern.search(line):
            capture_transactions = False
            continue

        # Para de capturar transações se encontrar "Notas explicativas" ou rodapé
        if "Notas explicativas" in line or "242025 B001A" in line:
            capture_transactions = False
            continue

        # Verificar se a linha é o cabeçalho da tabela de movimentações
        if re.search(r"data\s+descrição\s+entradas\s+R\$\s+saídas\s+R\$\s+saldo\s+R\$", line, re.IGNORECASE):
            capture_transactions = True
            continue

        # Captura transações dentro da seção de movimentações
        if capture_transactions:
            # Ignorar linhas com "SALDO APLIC AUT MAIS"
            if saldo_aplic_pattern.search(line):
                continue

            # Remover prefixos como "P = poupança automática"
            cleaned_line = line.strip()
            prefix_match = prefix_pattern.search(cleaned_line)
            if prefix_match:
                cleaned_line = prefix_match.group(2).strip()

            # Verificar se a linha contém uma data (DD/MM)
            if date_pattern.match(line):
                current_date = line[:5]  # Extrai a data (ex.: "05/03")
                if year:
                    full_date = f"{current_date}/{year}"  # Adiciona o ano (ex.: "05/03/2025")
                else:
                    full_date = current_date  # Fallback caso o ano não seja encontrado
                # Substitui a data original pela data completa
                formatted_line = f"{full_date} {line[5:].strip()}"
                # Extrair o primeiro valor monetário
                value_match = monetary_pattern.search(formatted_line)
                if value_match:
                    value = value_match.group(1)
                    # Determinar tipo (C ou D)
                    tipo = "D" if formatted_line.endswith("-") else "C"
                    # Remover o valor e o sufixo "-" da descrição
                    description = re.sub(monetary_pattern, "", line[5:]).replace("-", "").strip()
                    # Remover segundo valor monetário, se presente
                    description = re.sub(monetary_pattern, "", description).strip()
                    # Ajustar valor: remover ",00" se for número inteiro
                    if value.endswith(",00"):
                        value = value[:-3]
                    
                    # Ignorar descrições vazias
                    if not description:
                        continue
                    
                    transactions.append({
                        "Data": full_date,
                        "Descrição": description,
                        "Valor": value,
                        "Tipo": tipo
                    })
            # Captura linhas sem data, mas com valores monetários
            elif value_pattern.match(cleaned_line) and current_date:
                # Extrair o primeiro valor monetário
                value_match = monetary_pattern.search(cleaned_line)
                if value_match:
                    value = value_match.group(1)
                    # Determinar tipo (C ou D)
                    tipo = "D" if cleaned_line.endswith("-") else "C"
                    # Remover o valor e o sufixo "-" da descrição
                    description = re.sub(monetary_pattern, "", cleaned_line).replace("-", "").strip()
                    # Remover segundo valor monetário, se presente
                    description = re.sub(monetary_pattern, "", description).strip()
                    # Ajustar valor: remover ",00" se for número inteiro
                    if value.endswith(",00"):
                        value = value[:-3]
                    
                    # Ignorar descrições vazias
                    if not description:
                        continue
                    
                    if year:
                        full_date = f"{current_date}/{year}"
                    else:
                        full_date = current_date
                    
                    transactions.append({
                        "Data": full_date,
                        "Descrição": description,
                        "Valor": value,
                        "Tipo": tipo
                    })

    # Retorna todas as transações, sem filtrar duplicatas
    return transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato do Itaú3 (AM AUTO PECAS ACESS LTDA ME) e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)