import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato da Caixa para dividir transações, ignorando cabeçalho e rodapé.
    Combina NR. DOC. e HISTÓRICO em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Identificar início das transações (após "DATA MOV." e "HISTÓRICO")
    start_index = 0
    for i, line in enumerate(lines):
        if "DATA MOV." in line and "HISTÓRICO" in line:
            start_index = i + 1
            break
    
    # Identificar fim das transações (antes de mensagens como "* 661")
    end_index = len(lines)
    for i, line in enumerate(lines[start_index:], start=start_index):
        if line.startswith("*"):
            end_index = i
            break
    
    transaction_lines = lines[start_index:end_index]
    
    date_pattern = r"^\d{2}/\d{2}/\d{4}"
    value_pattern = r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+[CD]"
    
    transactions = []
    
    for line in transaction_lines:
        # Ignorar linhas de saldo ou totais
        if "SALDO DIA" in line or "Saldo" in line or not line:
            continue
        
        date_match = re.match(date_pattern, line)
        value_matches = list(re.finditer(value_pattern, line))
        
        if date_match and value_matches:
            date = date_match.group(0)
            value = value_matches[0].group(1)
            tipo = value_matches[0].group(0)[-1]  # 'C' ou 'D'
            
            # Extrair número do documento e histórico
            doc_start = date_match.end()
            doc_end = line.find(" ", doc_start)
            nr_doc = line[doc_start:doc_end].strip()
            
            desc_start = doc_end
            desc_end = value_matches[0].start()
            historico = line[desc_start:desc_end].strip()
            
            # Combinar NR. DOC. e HISTÓRICO em Descrição
            description = f"{nr_doc} {historico}".strip()
            
            # Ajustar valor: remover apenas o sinal de menos e manter formato com vírgula
            valor = value.replace("-", "").strip()
            
            # Remover ",00" se for um número inteiro
            if valor.endswith(",00"):
                valor = valor[:-3]
            
            transactions.append({
                "Data": date,
                "Descrição": description,
                "Valor": valor,
                "Tipo": tipo
            })
    
    return transactions

def extract_transactions(transactions):
    #Extrai os dados das transações (usado para compatibilidade com a estrutura).
    return transactions

def process(text):
    #Processa o texto extraído do extrato da Caixa e retorna o DataFrame, XML e TXT.
    return process_transactions(text, preprocess_text, extract_transactions)