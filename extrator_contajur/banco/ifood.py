import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato iFood, extraindo e formatando todas as transações.
    Retorna uma lista de dicionários com Data, Descrição, Valor e Tipo.
    Ignora cabeçalhos, rodapés, saldos e linhas mal formatadas.
    """
    # Dividir o texto em linhas
    linhas = text.splitlines()
    transactions = []
    transacao_atual = []
    encontrou_marcador_inicio = False
    ignorar_ate_data = False
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}')  # DD/MM/YYYY
    value_pattern = re.compile(r'(-?R\$\s*\d{1,3}(?:\.\d{3})*,\d{2})')  # R$ ou -R$ seguido de valor
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        # Corrigir tabulações nos valores (ex.: 1.055\t00 -> 1.055,00)
        linha = re.sub(r'(\d)\t(\d)', r'\1,\2', linha)
        # Normalizar espaços
        linha = re.sub(r'\s+', ' ', linha).strip()
        
        # Verificar se está ignorando até encontrar uma data
        if ignorar_ate_data:
            if date_pattern.match(linha):
                ignorar_ate_data = False
            else:
                continue
        
        # Identificar a linha "Data Movimentação Descrição da movimentação Valor"
        if "Data Movimentação Descrição da movimentação Valor" in linha:
            encontrou_marcador_inicio = True
            continue
        
        # Ignorar tudo antes do marcador inicial
        if not encontrou_marcador_inicio:
            continue
        
        # Ignorar cabeçalhos, rodapés, saldos e linhas com "Conta" seguido de número com hífen
        if any(phrase in linha for phrase in [
            "Extrato da Conta Digital iFood",
            "Solicitado em",
            "CNPJ",
            "Período selecionado",
            "Saldo disponível",
            "IFOOD.COM AGENCIA",
            "Em caso de dúvida",
            "Saldo do dia",
            "segunda a sexta",
        ]) or re.search(r'Conta\s+\d+-\d', linha):
            continue
            
        # Verificar se a linha começa com uma data
        if date_pattern.match(linha):
            # Processar a transação acumulada, se existir
            if transacao_atual:
                transacao_unificada = ' '.join(transacao_atual)
                
                # Extrair data
                partes = transacao_unificada.split()
                if not partes or not date_pattern.match(partes[0]):
                    transacao_atual = [linha]
                    continue
                data = partes[0]
                
                # Extrair valor
                valor_match = value_pattern.search(transacao_unificada)
                if not valor_match:
                    transacao_atual = [linha]
                    continue
                valor_str = valor_match.group(1)
                
                # Determinar tipo
                tipo = 'D' if valor_str.startswith('-R$') else 'C'
                
                # Formatando valor
                valor = valor_str.replace('R$', '').replace('-', '').strip()
                if valor.endswith(",00"):
                    valor = valor[:-3]
                elif valor.endswith("0"):
                    valor = valor[:-1]
                
                # Extrair descrição
                transacao_sem_data = ' '.join(partes[1:])
                descricao = transacao_sem_data.replace(valor_str, '').strip()
                
                # Criar dicionário da transação
                if descricao and valor:
                    transactions.append({
                        "Data": data,
                        "Descrição": descricao,
                        "Valor": valor,
                        "Tipo": tipo
                    })
            
            transacao_atual = [linha]
        else:
            transacao_atual.append(linha)
    
    # Processar a última transação
    if transacao_atual:
        transacao_unificada = ' '.join(transacao_atual)
        
        # Extrair data
        partes = transacao_unificada.split()
        if not partes or not date_pattern.match(partes[0]):
            return transactions
        data = partes[0]
        
        # Extrair valor
        valor_match = value_pattern.search(transacao_unificada)
        if not valor_match:
            return transactions
        valor_str = valor_match.group(1)
        
        # Determinar tipo
        tipo = 'D' if valor_str.startswith('-R$') else 'C'
        
        # Formatando valor
        valor = valor_str.replace('R$', '').replace('-', '').strip()
        if valor.endswith(",00"):
            valor = valor[:-3]
        elif valor.endswith("0"):
            valor = valor[:-1]
        
        # Extrair descrição
        transacao_sem_data = ' '.join(partes[1:])
        descricao = transacao_sem_data.replace(valor_str, '').strip()
        
        # Criar dicionário da transação
        if descricao and valor:
            transactions.append({
                "Data": data,
                "Descrição": descricao,
                "Valor": valor,
                "Tipo": tipo
            })
    
    return transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato iFood e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)
