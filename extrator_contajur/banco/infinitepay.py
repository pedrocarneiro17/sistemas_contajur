import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Pré-processa o texto do extrato da Caixa para dividir transações, ignorando cabeçalho e rodapé.
    Combina NR. DOC. e HISTÓRICO em uma única coluna Descrição.
    Mantém valores no formato brasileiro (ex.: 1.012,29).
    Suporta novo formato com 'Data Hora' e CNPJ inicial.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Lista de linhas a serem removidas (formato antigo)
    linhas_a_remover = [
        "Relatório de movimentações",
        "Data Tipo de transação Detalhe Valor (R$) Saldo (R$)",
    ]
    
    # Regex para formato antigo
    data_saldo_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+Saldo do dia\s+[\d,]+$')
    transacao_pattern = re.compile(r'^(.*?)\s+([+-][\d,.]+)$')
    
    # Se contém "Data Hora", processa como novo formato
    if 'Data Hora' in text:
        # Detecta CNPJ na primeira linha (formato XX.XXX.XXX/XXXX-XX)
        cnpj_pattern = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
        start_index = 9 if lines and cnpj_pattern.search(lines[0]) else 0
        
        # Padrões para ignorar no novo formato
        ignore_patterns = [
            r'^Relatório de movimentações$',
            r'^Data Hora Tipo de transação Nome Detalhe Valor \(R\ \$$',
            r'^A Central de Ajuda está disponível',
            r'^\d{2}/\d{2}/\d{4} - \d{2}/\d{2}/\d{4} Valor em R\$',
            r'^Saldo final do período',
            r'^R\$ 0,00 Total de entradas R\$',
            r'^Total de saídas R\$',
            r'^Página \d+ de \d+$',
        ]
        
        saldo_pattern = re.compile(r'^Saldo do dia R\$ [\d,.]+$')
        value_pattern = re.compile(r'([+-]\d{1,3}(?:\.\d{3})*(?:,\d{2})?)')
        date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        time_pattern = re.compile(r'^(\d{2}:\d{2})')
        
        transactions = []
        data_atual = None
        current_description = []
        
        for line in lines[start_index:]:
            if any(re.match(pat, line) for pat in ignore_patterns):
                continue
            
            if saldo_pattern.match(line):
                continue
            
            match_date = date_pattern.match(line)
            if match_date:
                data_atual = match_date.group(1)
                line_after = line[match_date.end():].strip()
                current_description = [line_after] if line_after else []
                continue
            
            match_time = time_pattern.match(line)
            if match_time and data_atual:
                if current_description:
                    full_desc = ' '.join(current_description).strip()
                    match_value = value_pattern.search(full_desc)
                    if match_value:
                        valor = match_value.group(1)
                        desc_clean = full_desc[:match_value.start()].strip()
                        tipo = 'C' if valor.startswith('+') else 'D'
                        valor_sem_sinal = valor[1:]
                        if valor_sem_sinal.endswith(',00'):
                            valor_sem_sinal = valor_sem_sinal[:-3]
                        transactions.append({
                            "Data": data_atual,
                            "Descrição": desc_clean,
                            "Valor": valor_sem_sinal,
                            "Tipo": tipo
                        })
                current_description = [line]
                continue
            
            if data_atual and current_description:
                current_description.append(line)
                continue
        
        # Processa a última descrição
        if data_atual and current_description:
            full_desc = ' '.join(current_description).strip()
            match_value = value_pattern.search(full_desc)
            if match_value:
                valor = match_value.group(1)
                desc_clean = full_desc[:match_value.start()].strip()
                tipo = 'C' if valor.startswith('+') else 'D'
                valor_sem_sinal = valor[1:]
                if valor_sem_sinal.endswith(',00'):
                    valor_sem_sinal = valor_sem_sinal[:-3]
                transactions.append({
                    "Data": data_atual,
                    "Descrição": desc_clean,
                    "Valor": valor_sem_sinal,
                    "Tipo": tipo
                })
        
        return transactions
    
    # Lógica original para o formato antigo
    transactions = []
    data_atual = None
    
    for line in lines:
        if not line.strip() or line in linhas_a_remover or line.startswith("Período de") or line.startswith("Nossa equipe de atendimento"):
            continue
        
        match_data_saldo = data_saldo_pattern.match(line)
        if match_data_saldo:
            data_atual = match_data_saldo.group(1)
            continue
        
        match_transacao = transacao_pattern.match(line)
        if match_transacao and data_atual:
            descricao = match_transacao.group(1).strip()
            valor = match_transacao.group(2)
            tipo = 'C' if valor.startswith('+') else 'D'
            valor_sem_sinal = valor[1:]
            if valor_sem_sinal.endswith(",00"):
                valor_sem_sinal = valor_sem_sinal[:-3]
            
            description = descricao
            
            transactions.append({
                "Data": data_atual,
                "Descrição": description,
                "Valor": valor_sem_sinal,
                "Tipo": tipo
            })
    
    return transactions

def extract_transactions(transactions):
    # Extrai os dados das transações (usado para compatibilidade com a estrutura).
    return transactions

def process(text):
    # Processa o texto extraído do extrato da Caixa e retorna o DataFrame, XML e TXT.
    return process_transactions(text, preprocess_text, extract_transactions)