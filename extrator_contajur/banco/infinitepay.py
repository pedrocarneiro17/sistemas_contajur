import re
# Presumindo que o módulo 'auxiliares' e a função 'process_transactions'
# estão disponíveis no caminho relativo, como no código original.
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato InfinitePay (Cloudwalk) para extrair transações.
    
    A lógica foi remodelada para ser mais robusta, garantindo:
    1. Propagação correta da data (DD/MM/YYYY) para todas as transações do dia.
    2. Captura correta de transações únicas no dia e transações com descrição longa.
    3. Ignorar cabeçalhos, rodapés de página e linhas de saldo.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    transactions = []
    current_date = None
    
    # --- 1. Padrões de Ignorar/Filtrar ---
    HEADER_TEXT = "Data Hora Tipo de transação Nome Detalhe Valor (R$)"
    # Ignora a linha de saldo. Usado também como delimitador para resetar a data.
    SALDO_PATTERN = re.compile(r'^Saldo do dia R\$ [\d,.]+$')
    # Início do bloco de rodapé que deve ser ignorado.
    FOOTER_START_PATTERN = re.compile(r'^A Central de Ajuda está disponível.*')
    
    # Padrão de valor para o final da linha: captura sinal e valor em formato brasileiro (ex: +1.234,56)
    VALUE_REGEX = r'([+-]\d{1,3}(?:\.\d{3})*(?:,\d{2}))$'
    
    # --- 2. Padrões de Transação (Mais robustos, usando '.*' guloso para a descrição) ---
    
    # Padrão para capturar a primeira transação do dia (contém DATA e HORA)
    # Grupo 1: Data | Grupo 2: Hora | Grupo 3: Descrição (tudo entre Hora e Valor) | Grupo 4: Valor assinado
    DATE_TRANSACTION_PATTERN = re.compile(
        r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s+(.*)\s+' + VALUE_REGEX
    )

    # Padrão para capturar transações subsequentes (contém apenas HORA)
    # Grupo 1: Hora | Grupo 2: Descrição (tudo entre Hora e Valor) | Grupo 3: Valor assinado
    TIME_TRANSACTION_PATTERN = re.compile(
        r'^(\d{2}:\d{2})\s+(.*)\s+' + VALUE_REGEX
    )
    
    # --- 3. Encontrar Ponto de Partida ---
    
    start_index = 0
    try:
        start_index = lines.index(HEADER_TEXT) + 1
    except ValueError:
        # Se o cabeçalho não for encontrado, tenta processar do início.
        pass
        
    lines = lines[start_index:]
    
    # --- 4. Iterar e Processar ---
    
    skip_footer_lines = 0 # Contador para ignorar o bloco de rodapé de 5 linhas
    
    for line in lines:
        
        # A. Lógica para pular o bloco de rodapé de 5 linhas
        if skip_footer_lines > 0:
            skip_footer_lines -= 1
            continue
        
        # B. Início do rodapé: pular esta linha e as 4 subsequentes (totalizando 5)
        if FOOTER_START_PATTERN.match(line):
            skip_footer_lines = 4 
            continue
        
        # C. Ignorar repetições do cabeçalho da tabela
        if line == HEADER_TEXT:
            continue

        # D. Ignorar "Saldo do dia" e resetar a data (fim do bloco de transações do dia)
        if SALDO_PATTERN.match(line):
            current_date = None 
            continue
            
        # E. Tentar parsear transação com DATA no início
        match_date_trans = DATE_TRANSACTION_PATTERN.match(line)
        if match_date_trans:
            # Captura e propaga a data
            current_date = match_date_trans.group(1)
            
            # Extrai os dados da transação
            hora = match_date_trans.group(2)
            descricao = match_date_trans.group(3).strip()
            valor_assinado = match_date_trans.group(4)
            
            # Processa o valor e tipo
            valor = valor_assinado[1:]
            tipo = 'C' if valor_assinado.startswith('+') else 'D'
            
            transactions.append({
                "Data": current_date,
                "Descrição": f"{hora} {descricao}".strip(),
                "Valor": valor,
                "Tipo": tipo
            })
            continue

        # F. Tentar parsear transação APENAS com HORA (usando a data atual propagada)
        match_time_trans = TIME_TRANSACTION_PATTERN.match(line)
        if match_time_trans and current_date:
            # Extrai os dados da transação
            hora = match_time_trans.group(1)
            descricao = match_time_trans.group(2).strip()
            valor_assinado = match_time_trans.group(3)
            
            # Processa o valor e tipo
            valor = valor_assinado[1:]
            tipo = 'C' if valor_assinado.startswith('+') else 'D'
            
            transactions.append({
                "Data": current_date,
                "Descrição": f"{hora} {descricao}".strip(),
                "Valor": valor,
                "Tipo": tipo
            })
            continue
            
        # G. Se chegou aqui, a linha não é uma transação válida ou é outro cabeçalho/lixo ignorável.
        pass

    return transactions

def extract_transactions(transactions):
    """
    Retorna as transações pré-processadas (para compatibilidade com a função process_transactions).
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato e retorna o DataFrame, XML e TXT.
    """
    # Delega o processamento final para a função utilitária
    return process_transactions(text, preprocess_text, extract_transactions)
