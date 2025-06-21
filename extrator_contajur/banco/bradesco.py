import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Bradesco para dividir transações, ignorando cabeçalho e rodapé.
    Combina número do documento e descrição em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Palavras-chave para filtrar linhas irrelevantes
    palavras_ignorar = [
        'Folha', 'Nome do usuário',
        'Data da operação', 'Saldos Invest Fácil', 'Os dados acima'
    ]
    
    # Padrões regex para identificar cabeçalhos/rodapés genéricos
    padroes_ignorar = [
        r'CNPJ:\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',  # CNPJ
        r'AGENCIA:\s*\d{4}-\d',                       # Agência
        r'CONTA:\s*\d+-\d',                           # Conta
        r'\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}' # Período (ex.: 01/04/2025 - 30/04/2025)
    ]
    
    # Padrão para limpar informações de empresa/CNPJ no início da linha
    padrao_limpeza_cabecalho = r'^.*?CNPJ:\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*\|?\s*'
    
    # Padrão para valores monetários
    padrao_valor_monetario = r'^-?\d+\.\d{3},\d{2}$|^-?\d+,\d{2}$'
    
    transactions = []
    i = 0
    found_saldo_anterior = False
    current_transacao = []
    current_data = None
    
    while i < len(lines):
        linha = lines[i].strip()
        
        # Ignorar linhas vazias ou que contenham palavras-chave irrelevantes
        if not linha or any(palavra in linha for palavra in palavras_ignorar):
            i += 1
            continue
        
        # Regra especial: se encontrar "Extrato Mensal", pular a linha atual e a próxima
        if 'Extrato Mensal' in linha:
            i += 2
            continue
        
        # Verificar se a linha contém "Total" seguido de um valor monetário
        if linha.startswith('Total') and i + 1 < len(lines):
            proxima_linha = lines[i + 1].strip()
            if re.match(padrao_valor_monetario, proxima_linha):
                break  # Parar, excluindo "Total" e tudo abaixo
        
        # Limpar informações de cabeçalho (ex.: "NOME DA EMPRESA | CNPJ: ...")
        linha_limpa = re.sub(padrao_limpeza_cabecalho, '', linha).strip()
        if not linha_limpa or any(re.search(padrao, linha_limpa) for padrao in padroes_ignorar):
            i += 1
            continue
        
        # Verificar se a linha contém "SALDO ANTERIOR"
        if "SALDO ANTERIOR" in linha:
            found_saldo_anterior = True
            i += 2  # Pular "SALDO ANTERIOR" e a linha seguinte (valor)
            continue
        
        # Após encontrar "SALDO ANTERIOR", processar as linhas
        if found_saldo_anterior:
            # Verificar se a linha é uma data (formato DD/MM/YYYY)
            if re.match(r'\d{2}/\d{2}/\d{4}', linha_limpa):
                # Se já existe uma transação acumulada, formatá-la e adicionar
                if current_transacao and len(current_transacao) >= 4:
                    descricao = f"{current_transacao[0]} {current_transacao[1]}"  # Combinar documento e descrição
                    valor = current_transacao[2].replace("-", "").strip()  # Remover sinal de menos
                    if valor.endswith(",00"):
                        valor = valor[:-3]  # Remover ",00" se for inteiro
                    tipo = "D" if current_transacao[2].startswith("-") else "C"  # Determinar tipo (C ou D)
                    transactions.append({
                        "Data": current_data,
                        "Descrição": descricao,
                        "Valor": valor,
                        "Tipo": tipo
                    })
                    current_transacao = []
                current_data = linha_limpa
            elif current_data:  # Linhas de transação
                # Verificar se a linha é um valor numérico (crédito, débito ou saldo)
                if re.match(padrao_valor_monetario, linha_limpa):
                    current_transacao.append(linha_limpa)
                    # Se já temos descrição, documento, crédito/débito e saldo, processar
                    if len(current_transacao) >= 4:
                        descricao = f"{current_transacao[0]} {current_transacao[1]}"  # Combinar documento e descrição
                        valor = current_transacao[2].replace("-", "").strip()  # Remover sinal de menos
                        if valor.endswith(",00"):
                            valor = valor[:-3]  # Remover ",00" se for inteiro
                        tipo = "D" if current_transacao[2].startswith("-") else "C"  # Determinar tipo (C ou D)
                        transactions.append({
                            "Data": current_data,
                            "Descrição": descricao,
                            "Valor": valor,
                            "Tipo": tipo
                        })
                        current_transacao = []
                else:
                    # Tratar número de documento ou descrição
                    if re.match(r'^\d+$', linha_limpa):  # Se for apenas número (documento)
                        if len(current_transacao) == 1:  # Já temos uma descrição
                            current_transacao.append(linha_limpa)  # Adicionar como documento
                        else:
                            current_transacao = [linha_limpa]  # Iniciar nova transação com documento
                    else:
                        # Se for uma descrição, concatenar com a anterior, se houver
                        if current_transacao and not re.match(r'^\d+$', current_transacao[-1]):
                            current_transacao[-1] = current_transacao[-1] + ' ' + linha_limpa
                        else:
                            current_transacao.append(linha_limpa)
        
        i += 1
    
    # Adicionar a última transação, se houver
    if current_transacao and len(current_transacao) >= 4 and current_data:
        descricao = f"{current_transacao[0]} {current_transacao[1]}"  # Combinar documento e descrição
        valor = current_transacao[2].replace("-", "").strip()  # Remover sinal de menos
        if valor.endswith(",00"):
            valor = valor[:-3]  # Remover ",00" se for inteiro
        tipo = "D" if current_transacao[2].startswith("-") else "C"  # Determinar tipo (C ou D)
        transactions.append({
            "Data": current_data,
            "Descrição": descricao,
            "Valor": valor,
            "Tipo": tipo
        })
    
    return transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato do Bradesco e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)