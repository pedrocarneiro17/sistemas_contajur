import re
from ..auxiliares.utils import process_transactions 

def preprocess_text(text):
    """
    Pré-processa o texto do extrato do Santander para extrair transações, ignorando cabeçalho e rodapé.
    Combina o histórico e o identificador em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    
    CORREÇÃO APLICADA: O padrão REGEX foi alterado para tratar o campo 'Documento' inconsistente
    e capturar o Histórico/Documento como um único grupo de descrição, ancorando no Valor e Saldo.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # PADRÃO CORRIGIDO: Data | Descrição (Histórico + Documento) | Valor | Saldo
    # Grupo 1: Data (DD/MM/YYYY)
    # Grupo 2: Descrição (Histórico e Documento combinados) - texto flexível (.+?)
    # Grupo 3: Valor (pt-BR)
    # Grupo 4: Saldo (pt-BR)
    date_pattern = r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-]?\d{1,3}(?:\.\d{3})*,\d{2})\s+([-]?\d{1,3}(?:\.\d{3})*,\d{2})$'
    
    transactions = []
    
    for line in lines:
        # Ignorar linhas de cabeçalho ou rodapé e a linha de cabeçalho da tabela
        if any(keyword in line for keyword in [
            "Aplicativo Santander", "Agência:", "Conta:", "Período:", "Data/Hora:", "Saldo disponível", 
            "Saldo de ContaMax", "Entenda a composição", "Central de Atendimento", "SAC", "Ouvidoria",
            "Data Histórico Documento Valor (R$) Saldo (R$)" 
        ]):
            continue
        
        # Processar linhas de transação
        match = re.match(date_pattern, line)
        if match:
            # Captura: Data (G1), Descrição Completa (G2), Valor (G3), Saldo (G4)
            data, description, valor_com_saldo, saldo_final = match.groups()
            
            valor = valor_com_saldo
            
            # Determinar o tipo de transação (D para negativo, C para positivo)
            tipo = "D" if valor.startswith("-") else "C"
            
            # Remover o sinal de menos
            valor = valor.replace("-", "").strip()
            
            # Ajustar valor: remover ",00" se for um número inteiro
            if valor.endswith(",00"):
                valor = valor[:-3]
                
            # A 'description' já contém o Histórico e o Documento
            description = description.strip()
            
            transactions.append({
                "Data": data,
                "Descrição": description,
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
    Processa o texto extraído do extrato do Santander e retorna o DataFrame, XML e TXT.
    """
    # Usa a função externa 'process_transactions' para gerar as saídas (DataFrame, XML, TXT)
    return process_transactions(text, preprocess_text, extract_transactions)