import re
# Remova ou ajuste este import conforme a estrutura real do seu projeto
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato bancário para extrair transações.
    A lógica foi adaptada para o formato específico do extrato fornecido anteriormente.
    - Inicia o processamento após a linha 'SALDO ANTERIOR'.
    - Para o processamento ao encontrar 'aviso:'.
    - Ignora linhas de saldo diário.
    - Extrai Data, Descrição e Valor de linhas de transação únicas.
    """
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # --- Padrões de Regex da nossa lógica validada ---
    # Padrão para identificar datas (DD/MM/AAAA) no início da linha
    date_pattern = r"^(\d{2}/\d{2}/\d{4})\s+"
    # Padrão para identificar o valor da transação no final da linha
    value_pattern = r"([-]?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
    
    transactions = []
    start_processing = False
    
    for line in lines:
        # Condição de parada do processamento
        if "aviso:" in line.lower():
            break
        
        # Condição de início do processamento
        if "saldo anterior" in line.lower():
            start_processing = True
            continue
        
        # Ignorar tudo que vem antes da linha de início
        if not start_processing:
            continue
        
        # Ignorar linhas de saldo que aparecem no meio do extrato
        if "saldo total disponível" in line.lower() or "saldo em conta corrente" in line.lower():
            continue
            
        # Tenta identificar uma transação completa (data e valor na mesma linha)
        date_match = re.match(date_pattern, line)
        value_match = re.search(value_pattern, line)
        
        if date_match and value_match:
            current_date = date_match.group(1)
            value_with_signal = value_match.group(1).strip()
            
            tipo = "D" if "-" in value_with_signal else "C"
            valor = value_with_signal.replace("-", "").strip()
            
            # Extrai a descrição removendo a data do início e o valor do final
            description_part = re.sub(date_pattern, "", line)
            description = re.sub(value_pattern, "", description_part).strip()
            
            transactions.append({
                "Data": current_date,
                "Descrição": description,
                "Valor": valor,
                "Tipo": tipo
            })
    
    # Remover transações duplicadas (lógica mantida do seu template)
    seen = set()
    unique_transactions = []
    for transaction in transactions:
        # Criar uma tupla com os campos para verificar duplicatas
        transaction_tuple = (transaction["Data"], transaction["Descrição"], transaction["Valor"], transaction["Tipo"])
        if transaction_tuple not in seen:
            seen.add(transaction_tuple)
            unique_transactions.append(transaction)
    
    # A função deve retornar a lista de dicionários
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
    # Esta função agora orquestra a chamada, passando as funções de extração como argumento
    return process_transactions(text, preprocess_text, extract_transactions)