import re

def identificar_banco(text):
    """
    Identifica o banco a partir do texto extraído do PDF.
    Retorna o nome do banco ou 'Banco não identificado'.
    """
    if not text:
        return "Erro: Texto vazio ou ilegível"

    linhas = text.splitlines()
    if not linhas:
        return "Erro: Texto vazio ou ilegível"
    palavras = text.split()
    
    if ("https://www.sicoob.com.br/sicoobnet/ib/#/home-extrato" in text):
        return "Sicoob2"
    
    if (palavras and palavras[0].lower().startswith('sicoob') or 'SICOOB CREDIMEPI' in text) or 'SICOOBCREDIMEPI' in text:
        return "Sicoob1"
    
    # Itaú4
    if 'Fale Conosco: www.itau.com.br/empresas.' in text:
        return "Itaú4"
    
    # Banco Inter 
    if 'Instituição: Banco Inter' in text:
        return "Banco Inter"
    
    # Nubank
    if 'nubank.com.br/contatos#ouvidoria' in text:
        return "Nubank"
    
    # Mercado Pago
    if 'www.mercadopago.com.br' in text or 'Mercado Pago' in text:
        return "Mercado Pago"
    
    # Efi
    if 'Efí S.A.' in text and 'Filtros aplicados' in text:
        return "Efi1"

    if 'Efí S.A.' in text and 'Filtros do' in text:
        return "Efi2"
    
        # Sicredi
    if 'Sicredi Fone' in text:
        return "Sicredi"
    
    # PagBank
    if 'PagSeguro Internet S/A' in text or '290-PagSeguroInternetS/A' in text:
        return "PagBank"
        # Stone
    if  'meajuda@stone.com.br' in text:
        return "Stone"
    
        # Banco do Brasil (variações)
    if '473-1' in text:
        return "Banco do Brasil2" if text.strip().split()[0].lower() == 'extrato' else "Banco do Brasil1"
    
    # Santander
    if 'Agência: 3472' in text or 'Agência: 3222' in text or 'Agência: 3503' in  text:
        return "Santander1"

    if 'EXTRATOCONSOLIDADOINTELIGENTE' in text or 'EXTRATO CONSOLIDADO INTELIGENTE' in  text or 'EXTRATO CONSOLIDADO' in text:
        return "Santander2"
    
    # Caixa
    if 'Sujeito a alteração até o final do expediente bancário' in text or 'Os lançamentos de extrato não estão disponíveis' in text or 'SAC CAIXA' in text:
        return "Caixa"
    
        # iFood
    if 'Extrato da Conta Digital iFood' in text:
        return "iFood"
    
    # Asaas
    if 'ASAAS Gestão Financeira Instituição de Pagamento S.A.' in text:
        return "Asaas"
    
    # Cora
    if 'Cora SCFI' in text:
        return "Cora"
    
    # Safra
    if 'Banco Safra S/A' in text:
        return "Safra"
    
    # InfinitePay
    if 'ajuda@infinitepay.io' in text:
        return "InfinitePay"

    # Bradesco
    if '00632' in text:
        return "Bradesco"
    
    # Sicoob (variações)

    
    if 'SICOOB - Sistema de Cooperativas de Crédito do Brasil' in text or 'SICOOB -Sistema de Cooperativas de Crédito do Brasil' in text or 'SISBR - SISTEMA DE INFORMÁTICA DO SICOOB' in  text:
        return "Sicoob3"

    if ("SISTEMA DE COOPERATIVAS DE CRÉDITO DO BRASIL" in text):
        return "Sicoob2"

    # Itaú (variações)

    if '8119' in text or '1472' in text or '3116' in text or '1300' in text:
        first_line = linhas[0].strip().lower()
        if re.match(r"^\s*extrato\s+mensal", first_line):
            return "Itaú3"
        if 'dados gerais' in first_line:
            for linha in linhas:
                if re.match(r"^\d{2}/\d{2}/\d{4}$", linha.strip()):
                    return "Itaú2"
        return "Itaú"

    return "Banco não identificado"