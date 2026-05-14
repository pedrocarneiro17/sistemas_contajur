# Automação GNRE/DIFAL em Lote

Envia guias GNRE de DIFAL para todos os estados via WebService do Portal Nacional GNRE, respeitando o limite de 50 guias por lote.

---

## Pré-requisitos

- Python 3.11+
- Certificado digital eCNPJ (A1 — arquivo `.pfx` ou `.p12`)
- Acesso liberado ao WebService GNRE (solicite em https://www.gnre.pe.gov.br)

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Configuração

1. Copie `.env.example` para `.env`
2. Preencha os campos:
   - `CNPJ_EMITENTE` — CNPJ da empresa (somente números)
   - `CERT_PATH` — caminho para o arquivo `.pfx` do eCNPJ
   - `CERT_PASSWORD` — senha do certificado
   - `ARQUIVO_ENTRADA` — planilha com os dados DIFAL
3. Solicite o acesso ao WebService no portal (necessário uma única vez por CNPJ)

---

## Planilha de entrada

Colunas obrigatórias:

| Coluna | Descrição | Exemplo |
|---|---|---|
| `uf` | Estado destinatário | `SP` |
| `cnpj_emitente` | CNPJ da empresa | `12345678000100` |
| `periodo_referencia` | Competência AAAAMM | `202501` |
| `valor_principal` | Valor do DIFAL | `1500.00` |

Colunas opcionais:

| Coluna | Descrição |
|---|---|
| `ie_emitente` | IE do emitente (vazio = ISENTO) |
| `juros` | Valor de juros |
| `multa` | Valor de multa |
| `cnpj_destinatario` | CNPJ do comprador (se exigido pela UF) |
| `cpf_destinatario` | CPF do comprador |
| `ie_destinatario` | IE do destinatário |
| `numero_doc_origem` | Nº da NF-e / chave de acesso |
| `data_vencimento` | Vencimento (AAAA-MM-DD) |
| `codigo_receita` | Código GNRE (vazio = 10008-0) |

Para gerar uma planilha de exemplo com todos os 27 estados:
```bash
python gerar_exemplo.py
```

---

## Uso

```bash
# Modo normal — envia ao portal
python main.py

# Arquivo específico
python main.py meus_dados.xlsx

# Dry-run — gera XMLs sem enviar (para testes)
python main.py --dry-run

# Dry-run com arquivo específico
python main.py meus_dados.xlsx --dry-run
```

---

## Saída

Os arquivos são gerados na pasta `saida/`:

```
saida/
├── xmls/
│   ├── lote_001.xml    # XML de cada lote enviado
│   ├── lote_002.xml
│   └── ...
├── resultado_gnre_YYYYMMDD_HHMMSS.xlsx   # Guias enviadas + resultados
└── protocolos_YYYYMMDD_HHMMSS.csv        # Log de protocolos por lote
```

---

## Limites do portal

| Limite | Valor |
|---|---|
| Máximo de guias por lote | 50 |
| Máximo de itens por guia | 100 |
| Máximo de itens por lote | 300 |

---

## Códigos de receita DIFAL

O código padrão é `10008-0` (ICMS — Diferencial de Alíquota — EC 87/2015).

Se algum estado exigir código específico, preencha a coluna `codigo_receita` na planilha ou ajuste o dicionário `CODIGO_RECEITA_DIFAL` em `models.py`.

Para estados que cobram **FCP** (Fundo de Combate à Pobreza), gere uma linha separada na planilha com o código de receita do FCP (ex: `10010-0`) e o valor correspondente.

---

## Troubleshooting

**Erro de certificado SSL**
- Verifique se o `CERT_PATH` aponta para o arquivo `.pfx` correto
- Confirme que a senha em `CERT_PASSWORD` está certa
- A validade do eCNPJ deve ser verificada junto à AC emissora

**"Acesso negado" ou 401**
- O WebService exige cadastro prévio do CNPJ no portal GNRE
- Acesse https://www.gnre.pe.gov.br e solicite o acesso

**Guias pendentes após processamento**
- Aumente `TENTATIVAS_CONSULTA` e `INTERVALO_CONSULTA_SEGUNDOS` em `config.py`
- O portal pode levar alguns minutos para processar lotes grandes

**UF retorna erro**
- Consulte o serviço `GnreConfigUF` para verificar os campos exigidos por aquele estado
- Alguns estados exigem CNPJ/CPF do destinatário — adicione na planilha
