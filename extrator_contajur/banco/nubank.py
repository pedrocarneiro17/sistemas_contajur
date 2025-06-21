import re
from ..auxiliares.utils import process_transactions

def preprocess_text(text):
    """
    Processa o texto completo do extrato extraído do PDF,
    aplica filtros, extrai data, descrição, valor e tipo da transação.
    Retorna uma lista de dicionários com as transações.
    """

    # --- FILTRAGEM PARA MANTER APENAS MOVIMENTAÇÕES ---
    linhas = text.splitlines()
    filtrado = []
    dentro_movimentacoes = False
    ignorar_rodape = False
    contador_rodape = 0

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        if linha.startswith("O saldo líquido"):
            break

        if linha.startswith("Tem alguma dúvida?"):
            ignorar_rodape = True
            continue

        if ignorar_rodape:
            if "Extrato gerado" in linha:
                contador_rodape = 0
                continue
            if contador_rodape <= 3:
                contador_rodape += 1
                continue
            else:
                ignorar_rodape = False
                contador_rodape = 0

        if "Movimentações" in linha or "MOVIMENTACOES" in linha:
            dentro_movimentacoes = True
            continue

        if dentro_movimentacoes:
            filtrado.append(linha)

    texto_filtrado = '\n'.join(filtrado)

    # --- SEPARAR DATA EM LINHA PRÓPRIA ---
    padrao_data = re.compile(r'(\d{2} (?:JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ) \d{4})', re.IGNORECASE)
    linhas = texto_filtrado.splitlines()
    resultado = []

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        match = padrao_data.search(linha)
        if match:
            data = match.group(1)
            conteudo = linha.replace(data, '').strip()
            resultado.append(data)
            if conteudo:
                resultado.append(conteudo)
        else:
            resultado.append(linha)
    texto_formatado = '\n'.join(resultado)

    # --- REMOVER LINHAS INDESJADAS ---
    linhas = texto_formatado.splitlines()
    resultado = []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if linha.lower().startswith("saldo do dia"):
            continue
        if linha.lower().startswith("total de entradas"):
            continue
        if linha.lower().startswith("crédito em conta"):
            continue
        if linha.lower().startswith("total de saídas") or linha.lower().startswith("total de saidas"):
            continue
        resultado.append(linha)
    texto_limpo = '\n'.join(resultado)

    # --- MANTER APENAS DATAS E LINHAS COM VALORES ---
    linhas = texto_limpo.splitlines()
    linhas_filtradas = []

    padrao_data_linha = re.compile(r'^\d{2} (?:JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ) \d{4}$', re.IGNORECASE)
    padrao_valor = re.compile(r'\d+[\.,]\d{2}')

    for linha in linhas:
        if padrao_data_linha.match(linha) or padrao_valor.search(linha):
            linhas_filtradas.append(linha)
    texto_final_bruto = '\n'.join(linhas_filtradas)

    # --- PADRONIZAR TRANSACOES COM DATA (data no formato dd/mm/aaaa) ---
    meses = {
        'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
        'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
        'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
    }
    padrao_data = re.compile(r'^(\d{2}) ([A-Z]{3}) (\d{4})$', re.IGNORECASE)

    linhas = texto_final_bruto.splitlines()
    data_atual = None
    transacoes = []

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        m = padrao_data.match(linha)
        if m:
            dia, mes_abr, ano = m.groups()
            mes_num = meses.get(mes_abr.upper(), '00')
            data_atual = f"{dia}/{mes_num}/{ano}"
        else:
            if data_atual:
                desc = linha

                # Extrair valor no final da linha (ex: 1.232,77 ou 100,00)
                m_valor = re.search(r'(\d{1,3}(?:\.\d{3})*|\d+),\d{2}$', desc)
                if m_valor:
                    valor_str = m_valor.group()

                    # Ajustar valor: se terminar com ',00' remover os centavos e pontos de milhar
                    if valor_str.endswith(",00"):
                        valor_formatado = valor_str[:-3].replace('.', '')
                    else:
                        valor_formatado = valor_str
                else:
                    valor_formatado = None

                # Remover valor da descrição
                if m_valor:
                    descricao = desc[:desc.rfind(valor_str)].strip()
                else:
                    descricao = desc.strip()

                # Determinar tipo: se contém 'transferência enviada' ou 'aplicação' é débito ('D'), senão crédito ('C')
                tipo_debito_indicadores = ['transferência enviada', 'aplicação', 'pagamento de boleto', 'aplicação', 'compra no débito']

                tipo = 'C'
                desc_lower = descricao.lower()
                for indicador in tipo_debito_indicadores:
                    if indicador in desc_lower:
                        tipo = 'D'
                        break

                if valor_formatado:
                    transacoes.append({
                        "Data": data_atual,
                        "Descrição": descricao,
                        "Valor": valor_formatado,
                        "Tipo": tipo
                    })

    return transacoes

def extract_transactions(transactions):
    """
    Extrai os dados das transações (usado para compatibilidade com a estrutura).
    Como preprocess_text já retorna os dados no formato correto, apenas retorna a lista.
    """
    return transactions

def process(text):
    """
    Processa o texto extraído do extrato do Nubank e retorna o DataFrame, XML e TXT.
    """
    return process_transactions(text, preprocess_text, extract_transactions)