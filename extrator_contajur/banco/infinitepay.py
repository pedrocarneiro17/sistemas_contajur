import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato da Caixa para dividir transações, ignorando cabeçalho e rodapé.
    Combina NR. DOC. e HISTÓRICO em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Lista de linhas a serem removidas
    linhas_a_remover = [
        "Relatório de movimentações",
        "Data Tipo de transação Detalhe Valor (R$) Saldo (R$)",
    ]
    
    # Regex para identificar linhas com data e saldo (ex.: "30/04/2025 Saldo do dia 158,07")
    data_saldo_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+Saldo do dia\s+[\d,]+$')
    
    # Regex para capturar descrição e valor da transação (ex.: "Pix De Implantare Odontologia Especializada Ltda +99,75")
    transacao_pattern = re.compile(r'^(.*?)\s+([+-][\d,.]+)$')
    
    transactions = []
    data_atual = None
    
    for line in lines:
        # Ignora linhas vazias ou na lista de exclusão
        if not line.strip() or line in linhas_a_remover or line.startswith("Período de") or line.startswith("Nossa equipe de atendimento"):
            continue
        
        # Verifica se a linha contém uma data e saldo
        match_data_saldo = data_saldo_pattern.match(line)
        if match_data_saldo:
            data_atual = match_data_saldo.group(1)  # Captura a data (ex.: "30/04/2025")
            continue  # Não inclui a linha de saldo
        
        # Verifica se a linha é uma transação válida
        match_transacao = transacao_pattern.match(line)
        if match_transacao and data_atual:
            descricao = match_transacao.group(1).strip()  # Captura a descrição
            valor = match_transacao.group(2)  # Captura o valor com sinal
            # Determina o tipo (C para positivo, D para negativo)
            tipo = 'C' if valor.startswith('+') else 'D'
            # Remove o sinal do valor
            valor_sem_sinal = valor[1:]  # Remove o '+' ou '-'
            # Remove ",00" se for um número inteiro
            if valor_sem_sinal.endswith(",00"):
                valor_sem_sinal = valor_sem_sinal[:-3]
            
            # Combina NR. DOC. e HISTÓRICO em Descrição (NR. DOC. é opcional)
            # Como não há NR. DOC. explícito no exemplo, usamos a descrição inteira
            description = descricao
            
            transactions.append({
                "Data": data_atual,
                "Descrição": description,
                "Valor": valor_sem_sinal,
                "Tipo": tipo
            })
    
    return transactions

def extract_transactions(transactions):
    # Extrai os dados das transações (usado para compatibilidade com a estrutura).
    return transactions

def process(text):
    # Processa o texto extraído do extrato da Caixa e retorna o DataFrame, XML e TXT.
    return process_transactions(text, preprocess_text, extract_transactions)