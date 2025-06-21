import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Santander para dividir transações.
    Remove cabeçalhos e rodapés específicos e extrai as transações.
    """
    # Dividir o texto em linhas
    linhas = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Extrair o ano da segunda linha (formato: mês/AAAA, ex.: Janeiro/2023 ou 01/2023)
    ano = None
    if len(linhas) >= 2:
        segunda_linha = linhas[1]
        match = re.search(r'(\w+)/(\d{4})', segunda_linha)
        if match:
            ano = match.group(2)
        else:
            print("Não foi possível extrair o ano da segunda linha.")
            return []
    
    # Primeiro filtro: Remover "EXTRATO CONSOLIDADO INTELIGENTE" e as 11 linhas seguintes
    i = 0
    while i < len(linhas):
        if 'extrato consolidado inteligente' in linhas[i].lower():
            del linhas[i:i+12]  # Remove a linha atual e as 11 seguintes
        else:
            i += 1
    
    # Segundo filtro: Remover "Extrato_PJ_A4_Inteligente" e as 9 linhas seguintes
    i = 0
    while i < len(linhas):
        if 'extrato_pj_a4_inteligente' in linhas[i].lower():
            del linhas[i:i+10]  # Remove a linha atual e as 9 seguintes
        else:
            i += 1
    
    # Terceiro filtro: Encontrar as posições das ocorrências de "saldo em"
    primeira_ocorrencia = -1
    segunda_ocorrencia = -1
    
    for i, linha in enumerate(linhas):
        if 'saldo em' in linha.lower():
            if primeira_ocorrencia == -1:
                primeira_ocorrencia = i
            elif segunda_ocorrencia == -1:
                segunda_ocorrencia = i
                break
    
    # Verificar se encontrou as ocorrências
    if primeira_ocorrencia == -1 or segunda_ocorrencia == -1:
        print("Não foram encontradas duas ocorrências de 'saldo em' no texto.")
        return []
    
    # Pegar apenas as linhas entre as ocorrências, excluindo a primeira ocorrência de "saldo em" e a linha seguinte
    linhas_filtradas = linhas[primeira_ocorrencia + 2:segunda_ocorrencia]
    
    # Quarto filtro: Processar transações
    padrao_data = r'^\d{2}/\d{2}(/\d{2,4})?$'
    padrao_valor = r'^-?\d{1,3}(\.\d{3})*,\d{2}-?$'
    
    transactions = []
    i = 0
    data_atual = None
    
    while i < len(linhas_filtradas):
        # Verificar se a linha é uma data
        data_match = re.match(padrao_data, linhas_filtradas[i].strip())
        if data_match:
            # Extrair a data e completar com o ano
            data = data_match.group(0)
            if not data.endswith(ano):  # Se a data não inclui o ano, adicionar
                data = f"{data}/{ano}"
            data_atual = data
            i += 1
            continue
        
        # Se temos uma data atual, processar a transação
        if data_atual:
            transacao = []
            valor = None
            while i < len(linhas_filtradas):
                linha = linhas_filtradas[i].strip()
                # Se encontrar uma nova data, parar a transação atual
                if re.match(padrao_data, linha):
                    break
                # Verificar se a linha contém um valor monetário
                if re.match(padrao_valor, linha):
                    if not valor:  # Considerar apenas o primeiro valor monetário
                        valor = linha
                    i += 1
                    # Continuar até encontrar uma nova data ou fim das linhas
                    while i < len(linhas_filtradas) and re.match(padrao_valor, linhas_filtradas[i].strip()):
                        i += 1  # Ignorar valores monetários adicionais
                    break
                transacao.append(linha)
                i += 1
            
            # Se encontrou um valor, processar a transação
            if valor and transacao:  # Apenas criar transação se houver descrição
                descricao = ' '.join(transacao).strip()
                # Determinar o tipo (C ou D) com base no sinal do valor
                tipo = 'D' if valor.endswith('-') else 'C'
                # Remover o sinal de menos do final, se presente
                valor = valor.rstrip('-')
                # Remover ",00" se for um número inteiro
                if valor.endswith(",00"):
                    valor = valor[:-3]
                
                transactions.append({
                    "Data": data_atual,
                    "Descrição": descricao,
                    "Valor": valor,
                    "Tipo": tipo
                })
        else:
            i += 1
    
    return transactions

def extract_transactions(transactions):
    """Extrai os dados das transações (usado para compatibilidade com a estrutura)."""
    return transactions

def process(text):
    """Processa o texto extraído do extrato do Santander e retorna o DataFrame, XML e TXT."""
    return process_transactions(text, preprocess_text, extract_transactions)
