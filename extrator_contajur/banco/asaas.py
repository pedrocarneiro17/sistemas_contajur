import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato ASAAS, extraindo e formatando todas as transações.
    Retorna uma lista de dicionários com Data, Descrição, Valor e Tipo.
    Ignora cabeçalhos, rodapés, saldos e linhas mal formatadas.
    """
    # Dividir o texto em linhas
    linhas = text.splitlines()
    transactions = []
    transacao_atual = []
    encontrou_marcador_inicio = False
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}')  # DD/MM/YYYY
    value_pattern = re.compile(r'R\$\s*-?\d{1,3}(?:\.\d{3})*,\d{2}')  # R$ ou R$ - seguido de valor
    
    for idx, linha in enumerate(linhas, 1):
        linha = linha.strip()
        if not linha:
            continue
        
        # Corrigir tabulações nos valores (ex.: 1.055\t00 -> 1.055,00)
        linha = re.sub(r'(\d)\t(\d)', r'\1,\2', linha)
        # Normalizar espaços
        linha = re.sub(r'\s+', ' ', linha).strip()
        
        # Identificar a linha "Data Movimentações Valor"
        if "Data Movimentações Valor" in linha:
            encontrou_marcador_inicio = True
            continue
        
        # Ignorar tudo antes do marcador inicial
        if not encontrou_marcador_inicio:
            continue
        
        # Ignorar cabeçalhos, rodapés, saldos e linhas com "Conta" seguido de número com hífen
        if any(phrase in linha for phrase in [
            "GERAR SAUDE E BEM ESTAR",
            "CNPJ",
            "Período",
            "Extrato gerado em",
            "Saldo inicial",
            "Saldo final",
            "ASAAS Gestão Financeira",
        ]) or re.search(r'Conta\s+\d+-\d', linha):
            continue
        
        # Adicionar linha à transação atual
        transacao_atual.append(linha)
        
        # Verificar se a transação atual forma uma transação válida
        transacao_unificada = ' '.join(transacao_atual)
        partes = transacao_unificada.split()
        
        if partes and date_pattern.match(partes[0]) and value_pattern.search(transacao_unificada):
            data = partes[0]
            valor_match = value_pattern.search(transacao_unificada)
            valor_str = valor_match.group(0)
            tipo = 'D' if 'R$ -' in valor_str else 'C'
            valor = valor_str.replace('R$', '').replace('-', '').strip()
            if valor.endswith(",00"):
                valor = valor[:-3]
            elif valor.endswith("0"):
                valor = valor[:-1]
            
            transacao_sem_data = ' '.join(partes[1:])
            descricao = transacao_sem_data.replace(valor_str, '').strip()
            
            if descricao and valor:
                transactions.append({
                    "Data": data,
                    "Descrição": descricao,
                    "Valor": valor,
                    "Tipo": tipo
                })
                transacao_atual = []  # Resetar após processar
        
        # Se for uma nova data, resetar transacao_atual após processar
        if idx < len(linhas) and date_pattern.match(linhas[idx].strip()):
            transacao_atual = []
    
    return transactions

def extract_transactions(transactions):
    """
    Retorna a lista de transações (mantido para compatibilidade).
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato ASAAS e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)