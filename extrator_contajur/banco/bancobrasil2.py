import re
from ..auxiliares.utils import process_transactions  

def preprocess_text(text):
    """
    Pré-processa o texto do extrato para extrair transações, ignorando cabeçalho e rodapé.
    Suporta os cabeçalhos: "Dia Lote Documento Histórico Valor" e "Dia Histórico Valor".
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
    
    # Marcadores de cabeçalho
    PADRAO_CABECALHO_1 = "Dia Lote Documento Histórico Valor"
    PADRAO_CABECALHO_2 = "Dia Histórico Valor"

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        # Corrigir tabulações nos valores (ex.: 2.865\t91 -> 2.865,91)
        linha = re.sub(r'(\d)\t(\d)', r'\1,\2', linha)
        # Normalizar espaços
        linha = re.sub(r'\s+', ' ', linha).strip()
        
        # Verificar se está ignorando até encontrar uma data (geralmente depois de um cabeçalho de nova página)
        if ignorar_ate_data:
            if date_pattern.match(linha):
                ignorar_ate_data = False
            else:
                continue
        
        # Identificar o marcador de início
        if PADRAO_CABECALHO_1 in linha or PADRAO_CABECALHO_2 in linha:
            encontrou_marcador_inicio = True
            continue
        
        # Ignorar tudo antes do marcador inicial
        if not encontrou_marcador_inicio:
            continue
        
        # Identificar "Extrato de Conta Corrente" e marcar para ignorar até a próxima data (cabeçalho de nova página)
        if "Extrato de Conta Corrente" in linha:
            ignorar_ate_data = True
            continue
        
        # Ignorar linhas com "S A L D O" ou "Saldo Anterior" ou "Total Aplicações"
        if re.search(r'saldo anterior|s a l d o|total aplicações', linha, re.IGNORECASE):
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
    
    # Filtrar linhas indesejadas nos dicionários (segurança)
    padrao_indesejado = re.compile(r'saldo anterior|s a l d o|total aplicações|limite ouro empresarial', re.IGNORECASE)
    transactions = [t for t in transactions if not padrao_indesejado.search(t['Descrição'])]
    
    return transactions

def extrair_dicionario(transacao):
    """
    Extrai um dicionário de uma transação unificada com Data, Descrição, Valor e Tipo.
    """
    partes = transacao.split()
    if len(partes) < 4:  # Precisa ter pelo menos data, descrição (mínimo 1), valor e tipo
        return None
    
    # Padrões Regex
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{2,4}')
    value_pattern = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2})')
    
    # 1. Extrair a data
    if not date_pattern.match(partes[0]):
        return None
    
    data = partes[0]
    
    # Corrigir datas incompletas/truncadas (ex.: "13/03/202 14024...")
    if len(data) == 8:  # Formato DD/MM/YY
        data = data[:6] + '20' + data[6:]
    elif len(data) > 10 and data.count('/') == 2:
         # Tenta isolar DD/MM/YYYY de lixos anexados
         match_date_full = re.search(r'(\d{2}/\d{2}/\d{4})', data)
         if match_date_full:
             data = match_date_full.group(1)
             # Reconstroi as partes para incluir o lixo na descrição
             resto = partes[0].replace(data, '').strip()
             partes.pop(0)
             if resto:
                 partes.insert(0, resto)
             partes.insert(0, data)
    
    # 2. Encontrar o valor monetário e seu tipo
    valor = None
    tipo = None
    idx_valor = -1
    
    for i, parte in enumerate(partes):
        match = value_pattern.match(parte)
        if match:
            # Encontrou o valor. Verifica o tipo na próxima parte.
            valor = match.group(1)
            idx_valor = i
            
            # O tipo é a parte seguinte (ex: (+), (-))
            if i + 1 < len(partes):
                prox_parte = partes[i + 1]
                if prox_parte == '(+)':
                    tipo = 'C'  # Crédito
                elif prox_parte == '(-)':
                    tipo = 'D'  # Débito
                else:
                    continue # Não é o tipo, continua procurando se o padrão é complexo.
            break
    
    # Ignorar transação se valor ou tipo for inválido
    if not valor or not tipo:
        return None
    
    # 3. Construir a descrição (tudo que está entre a data e o valor/tipo)
    # A descrição é tudo entre a data (índice 0) e o valor (índice idx_valor)
    descricao = ' '.join(partes[1:idx_valor]).strip()
    
    # O ajuste de valor foi removido conforme sua solicitação para manter o formato original.
    
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