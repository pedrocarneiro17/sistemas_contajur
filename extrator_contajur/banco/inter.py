import re
from ..auxiliares.utils import process_transactions  

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Banco Inter para extrair transações, ignorando cabeçalho e rodapé.
    Combina o tipo de transação e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Mapa de meses para conversão de data
    month_map = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04", "maio": "05", "junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
    }
    
    date_pattern = r"^(\d{1,2}) de ([A-Za-zç]+) de (\d{4})"
    value_pattern = r"([-]?R\$\s*\d{1,3}(?:\.\d{3})*,\d{2})"
    
    transactions = []
    current_date = None
    
    for line in lines:
        # Ignorar linhas de rodapé
        if "Fale com a gente" in line or "SAC:" in line or "Ouvidoria" in line or "Deficiência de fala" in line:
            continue
        
        # Verificar se a linha é uma data
        date_match = re.match(date_pattern, line, re.IGNORECASE)
        if date_match:
            day = date_match.group(1).zfill(2)  # Garantir dois dígitos
            month_name = date_match.group(2).lower()
            month = month_map.get(month_name, "01")  # Default para 01 se mês inválido
            year = date_match.group(3)
            current_date = f"{day}/{month}/{year}"
            continue
        
        # Ignorar linhas de saldo ou cabeçalho
        if any(keyword in line for keyword in ["Saldo do dia", "Saldo por transação", "Solicitado em", "CPF/CNPJ", "Período", "Saldo total", "Saldo disponível", "Saldo bloqueado"]):
            continue
        
        # Processar linhas de transação
        value_matches = list(re.finditer(value_pattern, line))
        if value_matches and current_date:
            value = value_matches[0].group(1)
            tipo = "D" if value.startswith("-") else "C"
            valor = value.replace("-", "").replace("R$", "").replace(" ", "").strip()
            
            # Ajustar valor: remover ",00" se for um número inteiro
            if valor.endswith(",00"):
                valor = valor[:-3]
            
            # Extrair descrição (tipo de transação + identificador)
            desc_start = 0
            desc_end = value_matches[0].start()
            description = line[desc_start:desc_end].strip()
            
            transactions.append({
                "Data": current_date,
                "Descrição": description,
                "Valor": valor,
                "Tipo": tipo
            })
    
    return transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato do Banco Inter e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)