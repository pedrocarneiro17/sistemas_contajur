# extrator_contajur/auxiliares/renomeador.py
import re
from datetime import datetime


class RenomeadorExtrato:
    """
    Classe para extrair informações de cliente e período dos extratos
    e gerar nomes padronizados para os arquivos.
    """
    
    def __init__(self):
        # Mapeamento de funções de extração por banco
        self.extractors = {
            "Sicoob1": self._extract_sicoob1,
            "Sicoob2": self._extract_sicoob2,
            "Sicoob3": self._extract_sicoob3,
            "Itaú": self._extract_itau,
            "Itaú2": self._extract_itau2,
            "Itaú3": self._extract_itau3,
            "Itaú4": self._extract_itau4,
            "Caixa": self._extract_caixa,
            "Banco Inter": self._extract_inter,
            "Nubank": self._extract_nubank,
            "Bradesco": self._extract_bradesco,
            "Santander1": self._extract_santander1,
            "Santander2": self._extract_santander2,
            "Sicredi": self._extract_sicredi,
            "PagBank": self._extract_pagbank,
            "Stone": self._extract_stone,
            "Banco do Brasil1": self._extract_bb1,
            "Banco do Brasil2": self._extract_bb2,
            "iFood": self._extract_ifood,
            "Asaas": self._extract_asaas,
            "Cora": self._extract_cora,
            "Safra": self._extract_safra,
            "InfinitePay": self._extract_infinitepay,
            "Efi1": self._extract_efi1,
            "Efi2": self._extract_efi2,
            "Mercado Pago": self._extract_mercadopago,
        }
    
    def gerar_nome_arquivo(self, texto, banco_identificado, nome_original="extrato"):
        """
        Gera o nome do arquivo no formato: CLIENTE_PERIODO.csv
        Ex: JOAO_SILVA_01-2024.csv
        
        Args:
            texto (str): Texto extraído do PDF
            banco_identificado (str): Nome do banco identificado
            nome_original (str): Nome original do arquivo (fallback)
            
        Returns:
            str: Nome do arquivo formatado
        """
        extractor = self.extractors.get(banco_identificado)
        
        if not extractor:
            return f"{nome_original}.csv"
        
        try:
            cliente, periodo = extractor(texto)
            
            if not cliente:
                cliente = "CLIENTE_NAO_IDENTIFICADO"
            
            if not periodo:
                periodo = "SEM_PERIODO"
            
            # Limpar e formatar o nome do cliente
            cliente = self._limpar_nome(cliente)
            
            # Formatar período
            periodo = self._formatar_periodo(periodo)
            
            return f"{cliente}_{periodo}.csv"
            
        except Exception as e:
            print(f"Erro ao extrair informações: {e}")
            return f"{nome_original}.csv"
    
    def _limpar_nome(self, nome):
        """Remove caracteres especiais e formata o nome"""
        # Remover pontuação, manter apenas letras, números e espaços
        nome = re.sub(r'[^\w\s-]', '', nome)
        # Substituir espaços por underscore
        nome = re.sub(r'\s+', '_', nome.strip())
        # Converter para maiúsculas
        nome = nome.upper()
        # Limitar tamanho
        return nome[:50]
    
    def _formatar_periodo(self, periodo):
        """
        Formata o período extraído para o padrão MM-YYYY ou DD-MM-YYYY_DD-MM-YYYY
        Remove barras e caracteres inválidos para nomes de arquivo
        """
        # Remover barras que causam problema no Windows
        periodo = periodo.replace('/', '-')
        
        # Remover espaços extras
        periodo = periodo.strip()
        
        # Se já está no formato correto, retornar
        if re.match(r'^\d{2}-\d{2}-\d{4}\s*-\s*\d{2}-\d{2}-\d{4}$', periodo):
            # Remover espaços ao redor do hífen separador
            periodo = re.sub(r'\s*-\s*', '_', periodo)
            return periodo
        
        # Tentar diversos padrões
        patterns = [
            (r'(\d{2})/(\d{4})', r'\1-\2'),  # 01/2024 -> 01-2024
            (r'(\d{2})/(\d{2})/(\d{4})', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),  # 01/01/2024 -> 01-01-2024
            (r'(\d{4})-(\d{2})', r'\2-\1'),  # 2024-01 -> 01-2024
            (r'(janeiro|jan)\s*(?:de\s*)?(\d{4})', lambda m: f"01-{m.group(2)}"),
            (r'(fevereiro|fev)\s*(?:de\s*)?(\d{4})', lambda m: f"02-{m.group(2)}"),
            (r'(março|mar)\s*(?:de\s*)?(\d{4})', lambda m: f"03-{m.group(2)}"),
            (r'(abril|abr)\s*(?:de\s*)?(\d{4})', lambda m: f"04-{m.group(2)}"),
            (r'(maio|mai)\s*(?:de\s*)?(\d{4})', lambda m: f"05-{m.group(2)}"),
            (r'(junho|jun)\s*(?:de\s*)?(\d{4})', lambda m: f"06-{m.group(2)}"),
            (r'(julho|jul)\s*(?:de\s*)?(\d{4})', lambda m: f"07-{m.group(2)}"),
            (r'(agosto|ago)\s*(?:de\s*)?(\d{4})', lambda m: f"08-{m.group(2)}"),
            (r'(setembro|set)\s*(?:de\s*)?(\d{4})', lambda m: f"09-{m.group(2)}"),
            (r'(outubro|out)\s*(?:de\s*)?(\d{4})', lambda m: f"10-{m.group(2)}"),
            (r'(novembro|nov)\s*(?:de\s*)?(\d{4})', lambda m: f"11-{m.group(2)}"),
            (r'(dezembro|dez)\s*(?:de\s*)?(\d{4})', lambda m: f"12-{m.group(2)}"),
        ]
        
        periodo_lower = periodo.lower()
        for pattern, replacement in patterns:
            match = re.search(pattern, periodo_lower, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                else:
                    return re.sub(pattern, replacement, periodo_lower, flags=re.IGNORECASE)
        
        return periodo
    # ==================== EXTRACTORS POR BANCO ====================
    
    def _extract_ifood(self, texto):
        """Extrai nome e período do iFood"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        
        # Nome está na primeira linha após "Extrato da Conta Digital iFood"
        if len(linhas) >= 1:
            primeira_linha = linhas[0].strip()
            match = re.search(r'Extrato da Conta Digital iFood\s+(.+)', primeira_linha)
            if match:
                cliente = match.group(1).strip()
        
        # Período: procurar linha com "Período selecionado"
        # Ex: "Período selecionado 01/04/2025 a 30/04/2025"
        match_periodo = re.search(
            r'Período selecionado\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})',
            texto
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        else:
            # Se não encontrar datas válidas, pegar datas do texto
            datas = re.findall(r'\d{2}/\d{2}/\d{4}', texto)
            # Filtrar datas válidas (não --/--/----)
            datas_validas = [d for d in datas if not d.startswith('--')]
            if len(datas_validas) >= 2:
                data_inicio = datas_validas[0].replace('/', '-')
                data_fim = datas_validas[-1].replace('/', '-')
                periodo = f"{data_inicio}_{data_fim}"
            else:
                # Se não achar nenhuma data válida, usar X
                periodo = "SEM_PERIODO"
        
        return cliente, periodo
    
    def _extract_safra(self, texto):
        """Extrai nome e período do Safra"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        
        # Nome está na segunda linha
        if len(linhas) >= 2:
            cliente = linhas[1].strip()
        
        # Período está na quarta linha
        if len(linhas) >= 4:
            linha_periodo = linhas[3].strip()
            # Extrair as duas datas (ex: "Período de 01/05/2025 a 31/05/2025")
            match = re.search(r'(\d{2})/(\d{2})/(\d{4})\s+a\s+(\d{2})/(\d{2})/(\d{4})', linha_periodo)
            if match:
                # Já formatar sem barras
                periodo = f"{match.group(1)}-{match.group(2)}-{match.group(3)}_{match.group(4)}-{match.group(5)}-{match.group(6)}"
        
        return cliente, periodo

    def _extract_asaas(self, texto):
        """Extrai nome e período do Asaas"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        
        # Nome está na primeira linha
        if len(linhas) >= 1:
            cliente = linhas[0].strip()
        
        # Período está na terceira linha (pulando linhas vazias)
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        if len(linhas_nao_vazias) >= 3:
            linha_periodo = linhas_nao_vazias[2]
            match = re.search(r'Período\s+(\d{2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+a\s+(\d{2})\s+de\s+(\w+)\s+de\s+(\d{4})', linha_periodo, re.IGNORECASE)
            if match:
                dia_inicio = match.group(1)
                mes_inicio = match.group(2)
                ano_inicio = match.group(3)
                dia_fim = match.group(4)
                mes_fim = match.group(5)
                ano_fim = match.group(6)
                
                # Converter mês por extenso para número
                meses = {
                    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                    'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                    'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                }
                
                mes_inicio_num = meses.get(mes_inicio.lower(), '01')
                mes_fim_num = meses.get(mes_fim.lower(), '12')
                
                # Já formatar sem barras, usando underscore como separador
                periodo = f"{dia_inicio}-{mes_inicio_num}-{ano_inicio}_{dia_fim}-{mes_fim_num}-{ano_fim}"
        
        return cliente, periodo
    
    def _extract_sicoob1(self, texto):
        """Extrai nome e período do Sicoob1"""
        cliente = None
        periodo = None
        
        # Procurar linha com "CONTA:"
        # Ex: "CONTA: 28.904.844-3 / GUIMARAES E DUTRA SERVICOS MEDICOS LTDA"
        match_cliente = re.search(r'CONTA:\s*[\d\.\-]+\s*/\s*(.+)', texto)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar linha com "PERÍODO:"
        # Ex: "PERÍODO: 01/04/2025 - 30/04/2025"
        match_periodo = re.search(
            r'PERÍODO:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})',
            texto
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo

    def _extract_sicredi(self, texto):
        """Extrai nome e período do Sicredi"""
        cliente = None
        periodo = None
        
        # Nome está após "Associado:"
        # Ex: "Associado: LOGIN TRANSPORTES E LOCACOES LTDA"
        match_cliente = re.search(r'Associado:\s*(.+)', texto)
        if match_cliente:
            # Pegar até quebra de linha ou até próxima informação
            linha_associado = match_cliente.group(1).strip()
            cliente = linha_associado.split('\n')[0].strip()
            # Remover possível "Cooperativa:" que pode vir junto
            cliente = cliente.split('Cooperativa:')[0].strip()
        
        # Período está em "Dados referentes ao período"
        # Ex: "Dados referentes ao período 01/04/2025 a 30/04/2025."
        match_periodo = re.search(
            r'período\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})',
            texto,
            re.IGNORECASE
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo

    def _extract_itau4(self, texto):
        """Extrai nome e período do Itaú4"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Procurar por CNPJ para pegar o nome
        for i, linha in enumerate(linhas_nao_vazias):
            # Padrão 1: Nome está após a linha do CNPJ
            if re.search(r'CNPJ\s+\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', linha):
                if i + 1 < len(linhas_nao_vazias):
                    possivel_nome = linhas_nao_vazias[i + 1]
                    # Verificar se não é uma palavra-chave
                    if not any(palavra in possivel_nome.upper() for palavra in ['SALDO', 'LIMITE', 'AGÊNCIA', 'CONTA']):
                        cliente = possivel_nome
                        break
            
            # Padrão 2: CNPJ vem depois do nome
            # Ex: "BRASILIS JOIAS E GEMAS LTDA." seguido de "06.938.834/0001-29"
            if re.match(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$', linha):
                if i > 0:
                    possivel_nome = linhas_nao_vazias[i - 1]
                    # Verificar se não é uma palavra-chave
                    if not any(palavra in possivel_nome.upper() for palavra in ['SALDO', 'LIMITE', 'AGÊNCIA', 'CONTA', 'EXTRATO']):
                        cliente = possivel_nome
                        break
        
        # Procurar período
        # Ex: "Lançamentos do período: 01/05/2025 até 31/05/2025"
        # ou "lançamentos período: 01/04/2025 até 30/04/2025"
        match_periodo = re.search(
            r'[Ll]ançamentos\s+(?:do\s+)?período:\s*(\d{2}/\d{2}/\d{4})\s+até\s+(\d{2}/\d{2}/\d{4})',
            texto
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo
    
    def _extract_inter(self, texto):
        """Extrai nome e período do Inter"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Nome está na segunda linha (não vazia)
        if len(linhas_nao_vazias) >= 2:
            cliente = linhas_nao_vazias[1]
        
        # Período está na quarta linha (não vazia)
        # Ex: "Período: 10/04/2025 a 10/05/2025"
        if len(linhas_nao_vazias) >= 4:
            linha_periodo = linhas_nao_vazias[3]
            match = re.search(r'Período:\s*(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', linha_periodo)
            if match:
                data_inicio = match.group(1).replace('/', '-')
                data_fim = match.group(2).replace('/', '-')
                periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo

    def _extract_nubank(self, texto):
        """Extrai nome e período do Nubank"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Nome está na primeira linha (não vazia)
        if len(linhas_nao_vazias) >= 1:
            cliente = linhas_nao_vazias[0]
        
        # Período está na quarta linha (não vazia)
        # Ex: "01 DE DEZEMBRO DE 2025 a 31 DE DEZEMBRO DE 2025 VALORES EM R$"
        if len(linhas_nao_vazias) >= 4:
            linha_periodo = linhas_nao_vazias[3]
            # Extrair datas por extenso
            match = re.search(
                r'(\d{2})\s+DE\s+(\w+)\s+DE\s+(\d{4})\s+a\s+(\d{2})\s+DE\s+(\w+)\s+DE\s+(\d{4})',
                linha_periodo,
                re.IGNORECASE
            )
            if match:
                dia_inicio = match.group(1)
                mes_inicio = match.group(2)
                ano_inicio = match.group(3)
                dia_fim = match.group(4)
                mes_fim = match.group(5)
                ano_fim = match.group(6)
                
                # Converter mês por extenso para número
                meses = {
                    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                    'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                    'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                }
                
                mes_inicio_num = meses.get(mes_inicio.lower(), '01')
                mes_fim_num = meses.get(mes_fim.lower(), '12')
                
                periodo = f"{dia_inicio}-{mes_inicio_num}-{ano_inicio}_{dia_fim}-{mes_fim_num}-{ano_fim}"
        
        return cliente, periodo
    
    def _extract_pagbank(self, texto):
        """Extrai nome e período do PagBank"""
        cliente = None
        periodo = None
        
        # Procurar nome
        match_cliente = re.search(r'(?:Nome|Titular)[:\s]+([\w\s]+)', texto, re.IGNORECASE)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar período
        match_periodo = re.search(r'Extrato de\s+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match_periodo:
            periodo = match_periodo.group(1)
        
        return cliente, periodo
    
    def _extract_bb2(self, texto):
        """Extrai nome e período do Banco do Brasil 2"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        
        # Nome está na segunda linha (após "Extrato de Conta Corrente")
        if len(linhas) >= 2:
            linha_cliente = linhas[1].strip()
            # Remover "Cliente" se vier no início
            cliente = linha_cliente.replace('Cliente', '').strip()
        
        # Período: pegar a penúltima data e a última data do texto
        datas = re.findall(r'\d{2}/\d{2}/\d{4}', texto)
        
        if len(datas) >= 2:
            # Penúltima data como início
            data_inicio = datas[-2]
            # Última data como fim
            data_fim = datas[-1]
            
            # Formatar sem barras
            data_inicio_fmt = data_inicio.replace('/', '-')
            data_fim_fmt = data_fim.replace('/', '-')
            periodo = f"{data_inicio_fmt}_{data_fim_fmt}"
        
        return cliente, periodo

    def _extract_bb1(self, texto):
        """Extrai nome e período do Banco do Brasil 1"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Procurar linha com "Conta corrente"
        # O nome vem na linha seguinte após o número da conta
        for i, linha in enumerate(linhas_nao_vazias):
            if linha == 'Conta corrente':
                # Próxima linha tem número-nome (ex: "7724-0JOAQUIM S F S ADV")
                if i + 1 < len(linhas_nao_vazias):
                    linha_conta = linhas_nao_vazias[i + 1]
                    # Extrair nome após o número da conta
                    # Padrão: XXXX-XNOME (sem espaço)
                    match = re.search(r'^\d+-\d(.+)', linha_conta)
                    if match:
                        cliente = match.group(1).strip()
                    break
        
        # Procurar linha com "Período do extrato"
        # Ex: "Período do extrato 03 / 2025"
        match_periodo = re.search(r'Período do extrato\s+(\d{2})\s*/\s*(\d{4})', texto)
        
        if match_periodo:
            mes = match_periodo.group(1)
            ano = match_periodo.group(2)
            data_inicio = f"01-{mes}-{ano}"
            
            # Última data do texto como fim
            datas = re.findall(r'(\d{2})/(\d{2})/(\d{4})', texto)
            if datas:
                # Pegar última data e formatar
                ultima_data = datas[-1]
                data_fim = f"{ultima_data[0]}-{ultima_data[1]}-{ultima_data[2]}"
                periodo = f"{data_inicio}_{data_fim}"
            else:
                # Se não achar data final, usar só mês/ano
                periodo = f"{mes}-{ano}"
        
        return cliente, periodo

    def _extract_mercadopago(self, texto):
        """Extrai nome e período do Mercado Pago"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Nome está após "EXTRATO DE CONTA"
        # Geralmente é a segunda linha não vazia
        for i, linha in enumerate(linhas_nao_vazias):
            if 'EXTRATO DE CONTA' in linha.upper():
                if i + 1 < len(linhas_nao_vazias):
                    possivel_nome = linhas_nao_vazias[i + 1]
                    # Verificar se não é CPF/CNPJ
                    if not re.search(r'\d{11}|\d{14}|CPF|CNPJ', possivel_nome):
                        cliente = possivel_nome
                        break
        
        # Período está em "Periodo:" ou "Período:"
        # Ex: "De 01-03-2025 al 31-03-2025" ou "Periodo: 01-03-2025 al 31-03-2025"
        match_periodo = re.search(
            r'(?:De\s+|Periodo:\s*|Período:\s*)(\d{2}[-/]\d{2}[-/]\d{4})\s+al?\s+(\d{2}[-/]\d{2}[-/]\d{4})',
            texto,
            re.IGNORECASE
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo

    def _extract_infinitepay(self, texto):
        """Extrai nome e período do InfinitePay"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Nome está na primeira linha antes do CNPJ
        # Ex: "TUMANOS STORE LTDA - CNPJ: 38.013.547/0001-02"
        if len(linhas_nao_vazias) >= 1:
            primeira_linha = linhas_nao_vazias[0]
            match = re.search(r'^(.+?)\s*-\s*CNPJ:', primeira_linha)
            if match:
                cliente = match.group(1).strip()
        
        # Período: procurar padrão de datas
        # Ex: "01/08/2025 - 31/08/2025"
        match_periodo = re.search(
            r'(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})',
            texto
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo 
    
    def _extract_pagbank(self, texto):
        """Extrai nome e período do PagBank"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Nome está na segunda linha (após "290 - PagSeguro Internet S/A")
        if len(linhas_nao_vazias) >= 2:
            cliente = linhas_nao_vazias[1]
        
        # Período está na linha "Periodo:"
        # Ex: "Periodo: 01/04/2025 a 30/04/2025"
        match_periodo = re.search(
            r'Periodo:\s*(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})',
            texto,
            re.IGNORECASE
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo

    def _extract_cora(self, texto):
        """Extrai nome e período do Cora"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Nome está na primeira linha
        if len(linhas_nao_vazias) >= 1:
            cliente = linhas_nao_vazias[0]
        
        # Período está em "Extrato do período"
        # Ex: "Extrato do período 01/04/2025 a 01/05/2025"
        match_periodo = re.search(
            r'Extrato do período\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})',
            texto,
            re.IGNORECASE
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo

    def _extract_stone(self, texto):
        """Extrai nome e período do Stone"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        linhas_nao_vazias = [l.strip() for l in linhas if l.strip()]
        
        # Procurar por "Nome" para pegar o cliente
        # A próxima linha terá o nome
        for i, linha in enumerate(linhas_nao_vazias):
            if linha == 'Nome' or linha == 'Titular':
                if i + 1 < len(linhas_nao_vazias):
                    cliente = linhas_nao_vazias[i + 1]
                    break
        
        # Período: procurar padrão "Período:" ou "Período  "
        # Ex: "Período: de 01/10/2025 a 31/10/2025"
        # ou "Período  01/04/2025 até 30/04/2025"
        match_periodo = re.search(
            r'Período:\s*(?:de\s+)?(\d{2}/\d{2}/\d{4})\s+(?:a|até)\s+(\d{2}/\d{2}/\d{4})',
            texto,
            re.IGNORECASE
        )
        if match_periodo:
            data_inicio = match_periodo.group(1).replace('/', '-')
            data_fim = match_periodo.group(2).replace('/', '-')
            periodo = f"{data_inicio}_{data_fim}"
        
        return cliente, periodo
        
    
    
    def _extract_sicoob2(self, texto):
        """Extrai nome e período do Sicoob2"""
        return self._extract_sicoob1(texto)  # Mesmo padrão
    
    def _extract_sicoob3(self, texto):
        """Extrai nome e período do Sicoob3"""
        return self._extract_sicoob1(texto)  # Mesmo padrão
    
    def _extract_itau(self, texto):
        """Extrai nome e período do Itaú"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        for linha in linhas:
            # Nome do cliente
            if 'ag' in linha.lower() and 'cc' in linha.lower():
                # Linha acima geralmente tem o nome
                idx = linhas.index(linha)
                if idx > 0:
                    cliente = linhas[idx - 1].strip()
            
            # Período
            if 'período' in linha.lower():
                match = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
                if match:
                    periodo = match.group(1)
        
        return cliente, periodo
    
    def _extract_itau2(self, texto):
        """Extrai nome e período do Itaú2"""
        return self._extract_itau(texto)
    
    def _extract_itau3(self, texto):
        """Extrai nome e período do Itaú3"""
        return self._extract_itau(texto)
    
    def _extract_caixa(self, texto):
        """Extrai nome e período da Caixa"""
        cliente = None
        periodo = None
        
        # Procurar nome após "Titular"
        match_cliente = re.search(r'Titular[:\s]+([\w\s]+)', texto, re.IGNORECASE)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar período
        match_periodo = re.search(r'Período[:\s]+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match_periodo:
            periodo = match_periodo.group(1)
        
        return cliente, periodo
    

    
    def _extract_bradesco(self, texto):
        """Extrai nome e período do Bradesco"""
        cliente = None
        periodo = None
        
        # Procurar nome
        match_cliente = re.search(r'(?:Nome|Cliente)[:\s]+([\w\s]+)', texto, re.IGNORECASE)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar período
        match_periodo = re.search(r'Período[:\s]+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match_periodo:
            periodo = match_periodo.group(1)
        
        return cliente, periodo
    
    def _extract_santander1(self, texto):
        """Extrai nome e período do Santander1"""
        cliente = None
        periodo = None
        
        linhas = texto.splitlines()
        for linha in linhas:
            # Nome
            if 'titular' in linha.lower():
                match = re.search(r'Titular[:\s]+([\w\s]+)', linha, re.IGNORECASE)
                if match:
                    cliente = match.group(1).strip()
            
            # Período
            if 'período' in linha.lower():
                match = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
                if match:
                    periodo = match.group(1)
        
        return cliente, periodo
    
    def _extract_santander2(self, texto):
        """Extrai nome e período do Santander2"""
        return self._extract_santander1(texto)
    

    def _extract_efi1(self, texto):
        """Extrai nome e período do Efi1"""
        cliente = None
        periodo = None
        
        # Procurar nome
        match_cliente = re.search(r'(?:Nome|Titular)[:\s]+([\w\s]+)', texto, re.IGNORECASE)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar período com "Filtros aplicados"
        match_periodo = re.search(r'Filtros aplicados.*?(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE | re.DOTALL)
        if match_periodo:
            periodo = match_periodo.group(1)
        
        return cliente, periodo
    
    def _extract_efi2(self, texto):
        """Extrai nome e período do Efi2"""
        cliente = None
        periodo = None
        
        # Procurar nome
        match_cliente = re.search(r'(?:Nome|Titular)[:\s]+([\w\s]+)', texto, re.IGNORECASE)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar período com "Filtros do"
        match_periodo = re.search(r'Filtros do.*?(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE | re.DOTALL)
        if match_periodo:
            periodo = match_periodo.group(1)
        
        return cliente, periodo
    
  
        """Extrai nome e período do Mercado Pago"""
        cliente = None
        periodo = None
        
        # Procurar nome
        match_cliente = re.search(r'(?:Nome|Conta)[:\s]+([\w\s]+)', texto, re.IGNORECASE)
        if match_cliente:
            cliente = match_cliente.group(1).strip()
        
        # Procurar período
        match_periodo = re.search(r'Período[:\s]+(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
        if match_periodo:
            periodo = match_periodo.group(1)
        
        return cliente, periodo