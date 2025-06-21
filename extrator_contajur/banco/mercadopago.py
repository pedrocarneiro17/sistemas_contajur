import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato para extrair transações, ignorando cabeçalho e rodapé.
    Combina o tipo de transação e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    Remove transações duplicadas (mesma data, descrição, valor e tipo).
    """
    # Divide o texto em linhas
    linhas = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Procura pela primeira linha que contém apenas "saldo" (case-insensitive)
    indice_saldo = None
    for i, linha in enumerate(linhas):
        if linha.strip().lower() == 'saldo':
            indice_saldo = i
            break
    
    # Se não encontrar "saldo", retorna vazio
    if indice_saldo is None:
        return []
    
    # Pega as linhas a partir da linha seguinte à que contém "saldo"
    linhas_filtradas = linhas[indice_saldo + 1:]
    
    # Lista de linhas a ignorar (case-insensitive)
    linhas_ignorar = {'data', 'descrição', 'id da operação', 'valor', 'saldo'}
    
    # Filtra as linhas, ignorando as especificadas e as que seguem o padrão xx/xx
    linhas_finais = []
    for linha in linhas_filtradas:
        linha_limpa = linha.strip().lower()
        if (linha_limpa not in linhas_ignorar and 
            not re.match(r'^\d{1,2}/\d{1,2}$', linha.strip(), re.IGNORECASE)):
            linhas_finais.append(linha.strip())
    
    # Padrão para identificar linhas de data (dd-mm-aaaa)
    padrao_data = re.compile(r'^\d{1,2}-\d{1,2}-\d{4}')
    
    # Lista para armazenar as transações concatenadas
    transacoes = []
    transacao_atual = []
    
    for linha in linhas_finais:
        if padrao_data.match(linha):
            if transacao_atual:
                transacoes.append(' '.join(transacao_atual))
                transacao_atual = []
        transacao_atual.append(linha)
    
    # Adiciona a última transação
    if transacao_atual:
        transacoes.append(' '.join(transacao_atual))
    
    # Lista para armazenar os dicionários das transações
    lista_transacoes = []
    
    # Padrão para identificar valores monetários (R$ seguido de número, com ou sem -)
    padrao_valor = re.compile(r'R\$ -?[\d,.]+')
    
    for transacao in transacoes:
        # Divide a transação em partes
        partes = transacao.split()
        
        # Extrai a data (primeiro elemento) e reformata com /
        data = partes[0].replace('-', '/')
        
        # Encontra todos os valores monetários na transação
        valores = padrao_valor.findall(transacao)
        if not valores:
            continue  # Pula transações sem valores válidos
        valor = valores[0]  # Pega o primeiro valor
        
        # Determina o tipo (D para débito, C para crédito)
        tipo = 'D' if valor.startswith('R$ -') else 'C'
        
        # Limpa o valor, removendo R$, - e mantendo formato brasileiro
        valor_limpo = valor.replace('R$ -', '').replace('R$', '').strip()
        # Remove ",00" para números inteiros
        if valor_limpo.endswith(',00'):
            valor_limpo = valor_limpo[:-3]
        
        # A descrição é tudo entre a data e o primeiro valor
        indice_valor = transacao.find(valores[0])
        descricao = transacao[len(partes[0]):indice_valor].strip()
        
        # Cria o dicionário da transação
        transacao_dict = {
            'Data': data,
            'Descrição': descricao,
            'Valor': valor_limpo,
            'Tipo': tipo
        }
        
        lista_transacoes.append(transacao_dict)
    
    # Remover transações duplicadas
    seen = set()
    unique_transactions = []
    for transaction in lista_transacoes:
        transaction_tuple = (transaction['Data'], transaction['Descrição'], transaction['Valor'], transaction['Tipo'])
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
    return process_transactions(text, preprocess_text, extract_transactions)

