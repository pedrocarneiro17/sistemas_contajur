import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato da Stone para dividir transações, ignorando cabeçalho e rodapé.
    Suporta os formatos 'Crédito/Débito' e 'Entrada/Saída'.
    Mantém valores no formato brasileiro (ex.: 1.012,29), removendo "R$".
    """
    # Dividir o texto em linhas
    linhas = [linha.strip() for linha in text.splitlines() if linha.strip()]
    
    # 1. IDENTIFICAR O FIM DO CABEÇALHO INICIAL
    # Identificar a primeira linha que contém "CONTRAPARTE"
    indice_contraparte = None
    for i, linha in enumerate(linhas):
        if "CONTRAPARTE" in linha:
            indice_contraparte = i
            break
    
    # Se encontrar "CONTRAPARTE", ignorar essa linha e tudo acima
    if indice_contraparte is not None:
        linhas_filtradas = linhas[indice_contraparte + 1:]
    else:
        linhas_filtradas = linhas  # Se não encontrar, mantém todas as linhas
    
    # 2. APLICAR LIMPEZAS INTERMEDIÁRIAS (Cabeçalhos Repetidos e Rodapé)
    linhas_intermediarias = []
    i = 0
    while i < len(linhas_filtradas):
        linha = linhas_filtradas[i]
        
        # Ignorar a linha com "DATA" (novo e antigo cabeçalho) e as 5 linhas seguintes.
        # Ambas as estruturas de cabeçalho da tabela (DATA...CONTRAPARTE) ocupam 6 linhas.
        if "DATA" in linha:
            i += 6  # Pular a linha atual e as próximas 5
            continue
        
        # Ignorar a linha com "Informações do Comprovante" e tudo abaixo
        if "Informações do Comprovante" in linha:
            break
        
        linhas_intermediarias.append(linha)
        i += 1
    
    # 3. PROCESSAR TRANSAÇÕES E SEPARAR EM VARIÁVEIS
    
    # Padrão de data flexível (DD/MM/YY ou DD/MM/YYYY)
    date_pattern = r"^\d{2}/\d{2}/\d{2,4}$"
    
    # Padrão de valor: aceita o formato brasileiro com ou sem R$ e sinal de menos, 
    # além de espaços opcionais (ex: - R$ 10.000,00).
    value_pattern = r"^-?\s*R?\s*\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}$" 
    
    # Mapeamento para suportar os dois formatos (antigo e novo)
    type_mapping = {
        "Débito": 'D',
        "Crédito": 'C',
        "Saída": 'D',
        "Entrada": 'C',
    }
    type_keywords = list(type_mapping.keys())
    
    transactions = []
    i = 0
    while i < len(linhas_intermediarias):
        linha = linhas_intermediarias[i]
        
        # Verificar se é uma data (início de uma transação)
        if re.match(date_pattern, linha):
            data = linha
            i += 1
            
            # Verificar o tipo (próxima linha) e usar o mapeamento
            if i < len(linhas_intermediarias) and linhas_intermediarias[i] in type_keywords:
                tipo = type_mapping[linhas_intermediarias[i]] # Usa o mapeamento
                i += 1
            else:
                continue  # Se não encontrar o tipo, pular para próxima data
            
            # Coletar a descrição até encontrar o valor
            descricao = []
            valor = None
            while i < len(linhas_intermediarias):
                linha_atual = linhas_intermediarias[i]
                
                # Verificar se é um valor monetário (novo e antigo formato)
                if re.match(value_pattern, linha_atual.strip()):
                    valor_raw = linha_atual.strip()
                    i += 1
                    
                    # LIMPEZA DO VALOR: remover "R$", espaços, '$' e o sinal de menos.
                    # O tipo (C/D) já define a direção da transação.
                    valor_limpo = valor_raw.replace("R$", "").replace("$", "").replace(" ", "").replace("-", "")
                    valor = valor_limpo.strip()
                    break
                
                # Se não é um valor, é parte da descrição
                descricao.append(linha_atual)
                i += 1
            
            # Se encontrou o valor, formar a transação
            if valor:
                # Juntar a descrição em uma única string
                descricao_texto = " ".join(descricao).strip() if descricao else ""
                
                valor_ajustado = valor
                
                # Remover ",00" se for um número inteiro (mantendo a lógica original)
                if valor_ajustado.endswith(",00"):
                    valor_ajustado = valor_ajustado[:-3]
                
                transactions.append({
                    "Data": data,
                    "Descrição": descricao_texto,
                    "Valor": valor_ajustado,
                    "Tipo": tipo
                })
            
            # Pular até a próxima data (ignorar saldo e contraparte)
            while i < len(linhas_intermediarias) and not re.match(date_pattern, linhas_intermediarias[i]):
                i += 1
        else:
            i += 1
    
    return transactions

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Neste caso, como já pré-processamos tudo, apenas retornamos as transações.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato da Stone e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)