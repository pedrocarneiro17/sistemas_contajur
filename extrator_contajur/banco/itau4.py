import re
# Remova ou ajuste este import conforme a estrutura real do seu projeto
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato bancário para extrair transações.
    Adaptado para o novo formato de extrato (Fitz):
    - Inicia após a linha contendo 'Saldo (R$)'.
    - Para ao encontrar 'Os saldos'.
    - Cada transação começa com uma data (DD/MM/YYYY) e termina na linha anterior à próxima data.
    - O valor é sempre a última linha do bloco de transação.
    - Aplica filtro para remover transações com 'SALDO TOTAL DISPONÍVEL DIA'.
    """
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # --- Padrões de Regex ---
    date_pattern = r"^\d{2}/\d{2}/\d{4}$"  # Data no formato DD/MM/YYYY
    # Padrão para identificar o valor no formato monetário (ex: 123.456,78 ou -123.456,78)
    # A âncora '$' garante que o valor seja o ÚLTIMO item na sua linha.
    value_pattern = r"([-]?\d{1,3}(?:\.\d{3})*,\d{2})$" 
    
    transactions = []
    start_processing = False
    current_transaction = []
    
    for line in lines:
        # Condição de parada do processamento
        if "Os saldos" in line:
            break
        
        # Condição de início do processamento
        if "Saldo (R$)" in line:
            start_processing = True
            continue
        
        # Ignorar linhas antes de começar o processamento
        if not start_processing:
            continue
        
        # Verifica se a linha começa com uma data
        if re.match(date_pattern, line):
            # Se encontramos uma nova data, processamos a transação anterior (se houver)
            if current_transaction:
                if len(current_transaction) >= 2:
                    data = current_transaction[0]
                    value_line = current_transaction[-1]
                    value_match = re.search(value_pattern, value_line)
                    
                    if value_match:
                        value_with_signal = value_match.group(1)
                        valor = value_with_signal.replace("-", "").strip()
                        
                        # Tipo: 'C' para valores sem sinal negativo, 'D' para valores negativos
                        tipo = "C" if "-" not in value_with_signal else "D"
                        
                        # Combina todas as linhas intermediárias como descrição (1: penúltima linha)
                        # Remove a linha do valor (current_transaction[-1])
                        descricao_lines = current_transaction[1:-1]
                        
                        # Limpa o valor restante da linha de descrição se ele ainda estiver lá
                        descricao_parts = []
                        for desc_line in descricao_lines:
                             descricao_parts.append(re.sub(value_pattern, "", desc_line).strip())
                             
                        # Junta as partes da descrição com um espaço
                        descricao = " ".join(descricao_parts).strip()
                        
                        transactions.append({
                            "Data": data,
                            "Descrição": descricao if descricao else "DESCRICAO VAZIA",
                            "Valor": valor,
                            "Tipo": tipo
                        })
                        
            # Inicia uma nova transação
            current_transaction = [line]
        elif start_processing:
            # Adiciona a linha à transação atual
            current_transaction.append(line)
    
    # Processa a última transação, se houver
    if current_transaction and len(current_transaction) >= 2:
        data = current_transaction[0]
        value_line = current_transaction[-1]
        value_match = re.search(value_pattern, value_line)
        
        if value_match:
            value_with_signal = value_match.group(1)
            valor = value_with_signal.replace("-", "").strip()
            tipo = "C" if "-" not in value_with_signal else "D"
            
            # Combina as linhas intermediárias como descrição
            descricao_lines = current_transaction[1:-1]
            descricao_parts = []
            for desc_line in descricao_lines:
                 descricao_parts.append(re.sub(value_pattern, "", desc_line).strip())
                 
            descricao = " ".join(descricao_parts).strip()
            
            transactions.append({
                "Data": data,
                "Descrição": descricao if descricao else "DESCRICAO VAZIA",
                "Valor": valor,
                "Tipo": tipo
            })

    # --- FILTRAGEM DE TRANSAÇÕES (EXCLUIR SALDOS) ---
    
    # Filtro para excluir transações que contêm "SALDO" na descrição (SALDO TOTAL DISPONÍVEL DIA)
    filtered_transactions = [
        t for t in transactions 
        if "SALDO" not in t["Descrição"].upper()
    ]

    # Remover transações duplicadas (mantendo sua lógica original)
    seen = set()
    unique_transactions = []
    for transaction in filtered_transactions:
        transaction_tuple = (transaction["Data"], transaction["Descrição"], transaction["Valor"], transaction["Tipo"])
        if transaction_tuple not in seen:
            seen.add(transaction_tuple)
            unique_transactions.append(transaction)
    
    return unique_transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato e retorna o resultado final
    através da função utilitária process_transactions.
    """
    return process_transactions(text, preprocess_text, extract_transactions)