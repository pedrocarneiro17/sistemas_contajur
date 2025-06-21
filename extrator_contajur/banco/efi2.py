import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    # Divide o texto em linhas
    linhas = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Filtra as linhas relevantes
    linhas_filtradas = []
    ignorar_ate_valor = True
    ignorar_proximas = 0
    
    for linha in linhas:
        if ignorar_proximas > 0:
            ignorar_proximas -= 1
            continue
        
        # Encontra o início das transações
        if ignorar_ate_valor and "VALOR (R$)" in linha:
            ignorar_ate_valor = False
            continue
        
        if ignorar_ate_valor:
            continue
        
        # Ignora blocos indesejados
        if "Efí S.A." in linha:
            ignorar_proximas = 13
            continue
        
        if "Saldo Diário" in linha:
            continue
        
        linhas_filtradas.append(linha)
    
    # Processa as transações
    transacoes = []
    transacao_atual = []
    data_atual = None
    
    data_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    valor_pattern = re.compile(r'^([+-]?\d{1,3}(?:\.\d{3})*,\d{2})$')
    
    for linha in linhas_filtradas:
        if data_pattern.match(linha):
            data_atual = linha
            continue
        
        valor_match = valor_pattern.match(linha)
        if valor_match:
            valor = valor_match.group(1)
            tipo = 'D' if '-' in valor else 'C'
            valor_formatado = valor.replace('-', '').replace('+', '')
            
            if transacao_atual and data_atual:
                descricao = ' '.join(transacao_atual).strip()
                
                # Remove ",00" se for um valor inteiro
                if valor_formatado.endswith(",00"):
                    valor_formatado = valor_formatado[:-3]
                
                transacoes.append({
                    "Data": data_atual,
                    "Descrição": descricao,
                    "Valor": valor_formatado,
                    "Tipo": tipo
                })
            
            transacao_atual = []
            continue
        
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
