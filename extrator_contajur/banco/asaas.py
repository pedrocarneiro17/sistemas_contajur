import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato ASAAS, extraindo e formatando todas as transações.
    Retorna uma lista de dicionários com Data, Descrição, Valor e Tipo.
    Ignora cabeçalhos, rodapés, saldos e linhas mal formatadas.
    Suporta descrições de transações que ocupam várias linhas.
    Processa transações a partir da linha após 'Valor', ignorando linhas específicas.
    """
    # Dividir o texto em linhas
    linhas = text.splitlines()
    transactions = []
    transacao_atual = []
    processar_transacoes = False
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')  # DD/MM/YYYY
    value_pattern = re.compile(r'R\$\s*-?\d{1,3}(?:\.\d{3})*,\d{2}')  # R$ ou R$ - seguido de valor
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        # Corrigir tabulações nos valores (ex.: 1.055\t00 -> 1.055,00)
        linha = re.sub(r'(\d)\t(\d)', r'\1,\2', linha)
        # Normalizar espaços
        linha = re.sub(r'\s+', ' ', linha).strip()
        
        # Verificar se encontramos a linha com "Valor" para começar o processamento
        if "Valor" == linha:
            processar_transacoes = True
            continue
        
        # Ignorar tudo antes de encontrar "Valor"
        if not processar_transacoes:
            continue
        
        # Ignorar linhas que começam com palavras específicas
        if any(linha.startswith(phrase) for phrase in [
            "Data",
            "Movimentações",
            "Valor",
            "ASAAS Gestão Financeira Instituição de Pagamento S.A.",
            "CNPJ:"
        ]):
            continue
        
        # Ignorar cabeçalhos, rodapés, saldos e linhas com "Conta" seguido de número com hífen
        if any(phrase in linha for phrase in [
            "GERAR SAUDE E BEM ESTAR",
            "Período",
            "Extrato gerado em",
            "Saldo inicial",
            "Saldo final"
        ]) or re.search(r'Conta\s+\d+-\d', linha):
            continue
        
        # Adicionar linha à transação atual
        transacao_atual.append(linha)
        
        # Verificar se a linha contém um valor (indica fim da transação)
        if value_pattern.search(linha):
            transacao_unificada = ' '.join(transacao_atual)
            partes = transacao_unificada.split()
            if partes and date_pattern.match(partes[0]):
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
            transacao_atual = []
        
        # Se a próxima linha for uma data, resetar transacao_atual
        elif transacao_atual and len(linhas) > linhas.index(linha) + 1:
            proxima_linha = linhas[linhas.index(linha) + 1].strip()
            if date_pattern.match(proxima_linha):
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
                transacao_atual = []
    
    # Processar a última transação, se houver
    if transacao_atual:
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