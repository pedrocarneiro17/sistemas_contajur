import re
# A importação abaixo é relativa à estrutura do seu projeto
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Bradesco para dividir transações, ignorando cabeçalho e rodapé.
    A descrição inclui todo o texto entre a data e o primeiro valor monetário, com palavras indesejadas removidas.
    Usa apenas o primeiro valor monetário para Valor e Tipo (C/D). O segundo valor monetário (saldo) é descartado.
    Remove palavras indesejadas como 'Dcto.', 'Crédito (R$)', 'Débito (R$)' e 'Saldo (R$)' da descrição.
    Retorna uma lista de dicionários com Data, Descrição, Valor e Tipo (C/D).
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Palavras-chave para filtrar linhas irrelevantes
    palavras_ignorar = [
        'Folha', 'Nome do usuário',
        'Data da operação', 'Os dados acima'
    ]
    
    # Palavras a serem removidas da descrição
    palavras_remover_descricao = [
        r'\bDcto\.\s*',              # Corresponde a "Dcto." com possíveis espaços
        r'\bCrédito\s*\(R\$\)\s*',   # Corresponde a "Crédito (R$)" com espaços
        r'\bDébito\s*\(R\$\)\s*',    # Corresponde a "Débito (R$)" com espaços
        r'\bSaldo\s*\(R\$\)\s*',     # Corresponde a "Saldo (R$)" com espaços
        r'\bÚltimos\s*Lançamentos\b',
        r'\bData\b',
        r'\bLançamento\b'
    ]
    
    # Padrões regex para identificar cabeçalhos/rodapés genéricos
    padroes_ignorar = [
        r'CNPJ:\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',  # CNPJ
        r'AGENCIA:\s*\d{4}-\d',                      # Agência
        r'CONTA:\s*\d+-\d',                          # Conta
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
    found_first_value = False  # Flag para rastrear se o primeiro valor monetário foi encontrado
    
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
        
        # Parar ao encontrar "SALDO INVEST FÁCIL" e a próxima linha for um valor monetário
        if 'SALDO INVEST FÁCIL' in linha and i + 1 < len(lines):
            proxima_linha = lines[i + 1].strip()
            if re.match(padrao_valor_monetario, proxima_linha):
                break
        
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
                # Se já existe uma transação acumulada com pelo menos uma descrição e um valor monetário
                if current_transacao and found_first_value:
                    # A descrição é tudo até o primeiro valor monetário
                    descricao = ' '.join(current_transacao[:-1]).strip()
                    for palavra in palavras_remover_descricao:
                        descricao = re.sub(palavra, '', descricao, flags=re.IGNORECASE)
                    descricao = ' '.join(descricao.split())
                    valor = current_transacao[-1].replace("-", "").strip()
                    tipo = "D" if current_transacao[-1].startswith("-") else "C"
                    if descricao and not 'Total' in descricao:
                        transactions.append({
                            "Data": current_data,
                            "Descrição": descricao,
                            "Valor": valor,
                            "Tipo": tipo
                        })
                # Inicia uma nova transação
                current_transacao = []
                current_data = linha_limpa
                found_first_value = False
            elif current_data:  # Linhas de transação
                # Verificar se a linha é um valor numérico (crédito, débito ou saldo)
                if re.match(padrao_valor_monetario, linha_limpa):
                    if found_first_value:
                        # Se já encontramos o primeiro valor monetário, ignorar o segundo (saldo)
                        current_transacao = []  # Reinicia para a próxima transação
                        found_first_value = False
                    else:
                        # Primeiro valor monetário encontrado
                        current_transacao.append(linha_limpa)
                        found_first_value = True
                        # Processar a transação imediatamente
                        if current_transacao:
                            descricao = ' '.join(current_transacao[:-1]).strip()
                            for palavra in palavras_remover_descricao:
                                descricao = re.sub(palavra, '', descricao, flags=re.IGNORECASE)
                            descricao = ' '.join(descricao.split())
                            valor = current_transacao[-1].replace("-", "").strip()
                            tipo = "D" if current_transacao[-1].startswith("-") else "C"
                            if descricao and not 'Total' in descricao:
                                transactions.append({
                                    "Data": current_data,
                                    "Descrição": descricao,
                                    "Valor": valor,
                                    "Tipo": tipo
                                })
                            current_transacao = []
                            found_first_value = False
                else:
                    # Acumular tudo que não é valor monetário como parte da descrição
                    linha_descricao = linha_limpa
                    for palavra in palavras_remover_descricao:
                        linha_descricao = re.sub(palavra, '', linha_descricao, flags=re.IGNORECASE)
                    linha_descricao = ' '.join(linha_descricao.split())
                    if linha_descricao:
                        current_transacao.append(linha_descricao)
        
        i += 1
    
    # Adicionar a última transação, se houver
    if current_transacao and found_first_value and current_data:
        # A descrição é tudo até o primeiro valor monetário
        descricao = ' '.join(current_transacao[:-1]).strip()
        for palavra in palavras_remover_descricao:
            descricao = re.sub(palavra, '', descricao, flags=re.IGNORECASE)
        descricao = ' '.join(descricao.split())
        valor = current_transacao[-1].replace("-", "").strip()
        tipo = "D" if current_transacao[-1].startswith("-") else "C"
        if descricao and not 'Total' in descricao:
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