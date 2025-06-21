import re
from ..auxiliares.utils import process_transactions  

def preprocess_text(text):
    """
    Pré-processa o texto do extrato da LOFT DA SERRA LTDA para extrair transações, ignorando cabeçalho e rodapé.
    Combina o tipo de transação e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    """
    # Dividir o texto em linhas
    linhas = text.splitlines()
    transactions = []
    transacao_atual = []
    encontrou_marcador_inicio = False
    ignorar_ate_data = False
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{2,4}')  # Aceita DD/MM/YY e DD/MM/YYYY
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        # Corrigir tabulações nos valores (ex.: 2.865\t91 -> 2.865,91)
        linha = re.sub(r'(\d)\t(\d)', r'\1,\2', linha)
        # Normalizar espaços
        linha = re.sub(r'\s+', ' ', linha).strip()
        
        # Verificar se está ignorando até encontrar uma data
        if ignorar_ate_data:
            if date_pattern.match(linha):
                ignorar_ate_data = False
            else:
                continue
        
        # Identificar a linha "Dia Lote Documento Histórico Valor"
        if "Dia Lote Documento Histórico Valor" in linha:
            encontrou_marcador_inicio = True
            continue
        
        # Ignorar tudo antes do marcador inicial
        if not encontrou_marcador_inicio:
            continue
        
        # Identificar "Extrato de Conta Corrente" e marcar para ignorar até a próxima data
        if "Extrato de Conta Corrente" in linha:
            ignorar_ate_data = True
            continue
        
        # Ignorar linhas com "S A L D O" ou "Saldo Anterior"
        if re.search(r'saldo anterior|s a l d o', linha, re.IGNORECASE):
            continue
        
        # Verificar se a linha começa com uma data
        if date_pattern.match(linha):
            # Processar a transação acumulada, se existir
            if transacao_atual:
                transacao_unificada = ' '.join(transacao_atual)
                dicionario = extrair_dicionario(transacao_unificada)
                if dicionario:
                    transactions.append(dicionario)
            transacao_atual = [linha]
        else:
            transacao_atual.append(linha)
    
    # Processar a última transação
    if transacao_atual:
        transacao_unificada = ' '.join(transacao_atual)
        dicionario = extrair_dicionario(transacao_unificada)
        if dicionario:
            transactions.append(dicionario)
    
    # Filtrar linhas indesejadas nos dicionários
    padrao_saldo = re.compile(r'saldo anterior|s a l d o', re.IGNORECASE)
    transactions = [t for t in transactions if not padrao_saldo.search(t['Descrição'])]
    
    return transactions

def extrair_dicionario(transacao):
    """
    Extrai um dicionário de uma transação unificada com Data, Descrição, Valor e Tipo.
    """
    partes = transacao.split()
    if len(partes) < 4:  # Precisa ter pelo menos data, descrição, valor e tipo
        return None
    
    # Extrair a data
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{2,4}')
    if not date_pattern.match(partes[0]):
        return None
    data = partes[0]
    # Corrigir datas no formato DD/MM/YY ou DD/MM/YYYY
    if len(data) == 8:  # Formato DD/MM/YY
        data = data[:6] + '20' + data[6:]
    elif len(data) == 11:  # Formato DD/MM/YYYYY (ex.: 13/03/20202)
        data = data[:6] + '2025'
    
    # Encontrar o primeiro valor monetário e seu tipo
    value_pattern = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}')
    valor = None
    tipo = None
    idx_valor = -1
    for i, parte in enumerate(partes):
        if value_pattern.match(parte):
            valor = parte
            idx_valor = i
            if i + 1 < len(partes):
                tipo = partes[i + 1]
                if tipo == '(+)':
                    tipo = 'C'
                elif tipo == '(-)':
                    tipo = 'D'
                else:
                    tipo = None
            break
    
    # Ignorar transação se valor ou tipo for inválido
    if not valor or not tipo:
        return None
    
    # Construir a descrição
    desc_inicial = ' '.join(partes[1:idx_valor]).strip()
    desc_final = ' '.join(partes[idx_valor + 2:]).strip() if idx_valor + 2 < len(partes) else ''
    descricao = f"{desc_inicial} {desc_final}".strip() if desc_final else desc_inicial
    
    # Ajustar valor: remover ",00" para inteiros e zero à direita para centavos (ex.: 123,30 -> 123,3)
    if valor.endswith(",00"):
        valor = valor[:-3]
    elif valor.endswith("0"):
        valor = valor[:-1]
    
    return {
        "Data": data,
        "Descrição": descricao,
        "Valor": valor,
        "Tipo": tipo
    }

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    return process_transactions(text, preprocess_text, extract_transactions)