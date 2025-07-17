import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    # Divide o texto em linhas
    linhas = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Processa as linhas com filtros e cria dicionários diretamente
    transacoes = []
    ignorar_ate_valor = True
    ignorar_proximas = 0
    transacao_atual = []
    data_atual = None
    
    data_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    valor_pattern = re.compile(r'^([+-]?\d{1,3}(?:\.\d{3})*,\d{2})$')
    
    for linha in linhas:
        if ignorar_proximas > 0:
            ignorar_proximas -= 1
            continue
        
        # Filtro: Ignora tudo antes de "VALOR (R$)"
        if ignorar_ate_valor and "VALOR (R$)" in linha.upper():
            ignorar_ate_valor = False
            continue
        
        if ignorar_ate_valor:
            continue
        
        # Filtro: Ignora "EFÍ S.A." e as 13 linhas seguintes
        if "EFÍ S.A." in linha.upper():
            ignorar_proximas = 13
            continue

        # Filtro: Ignora "Saldo do dia"
        if "SALDO DO DIA" in linha.upper():
            continue

        # Processa a transação
        # Se for uma data, inicia uma nova transação
        if data_pattern.match(linha):
            data_atual = linha
            transacao_atual = []
            continue
        
        # Se for um valor, finaliza a transação
        valor_match = valor_pattern.match(linha)
        if valor_match:
            valor = valor_match.group(1)
            valor_formatado = valor.replace('-', '').replace('+', '')
            if valor_formatado.endswith(",00"):
                valor_formatado = valor_formatado[:-3]
                
            # Verifica se transacao_atual e data_atual existem antes de processar
            if transacao_atual and data_atual:
                # Normaliza a descrição removendo caracteres indesejados
                descricao = ' '.join(transacao_atual).strip().replace('\n', ' ').replace('\r', ' ')
                # Lista de palavras-chave para tipo 'C' (crédito)
                credit_keywords = ['recebimento', 'venda na', 'pix recebido']
                # Verifica se é uma transação de crédito, mas não uma tarifa
                is_credit = any(keyword in descricao.lower() for keyword in credit_keywords) and 'tarifa' not in descricao.lower()
                tipo = 'C' if is_credit else 'D'
                transacoes.append({
                    "Data": data_atual,
                    "Descrição": descricao,
                    "Valor": valor_formatado,
                    "Tipo": tipo
                })
            transacao_atual = []
            continue
        
        # Linhas intermediárias são adicionadas à transação atual
        transacao_atual.append(linha)
    
    return transacoes

def extract_transactions(transactions):
    """
    Função de compatibilidade que simplesmente retorna as transações.
    Pode ser usada para transformações adicionais se necessário.
    """
    return transactions

def process(text):
    # Processa as transações
    return process_transactions(text, preprocess_text, extract_transactions)