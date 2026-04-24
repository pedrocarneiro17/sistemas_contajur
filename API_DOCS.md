# Documentação da API

API REST para processamento de extratos bancários e reconciliação de boletos pagos.

## URLs

| Ambiente | URL base |
|----------|----------|
| Produção | `https://sistemas-contajur.up.railway.app` |
| Local (teste) | `https://sistemas-contajur.up.railway.app` |

Para rodar localmente:

```bash
python api_server.py
```

---

## Endpoints

### `GET /api/health`

Verifica se o servidor está funcionando.

**Resposta**
```json
{
  "status": "OK",
  "message": "API funcionando"
}
```

---

### `POST /api/extratos/processar`

Recebe um PDF de extrato bancário e retorna as transações extraídas.

**Bancos suportados**

Asaas, Banco do Brasil, Bradesco, Caixa, Cora, Efi, iFood, InfinitePay, Inter, Itaú, Mercado Pago, Nubank, PagBank, Safra, Santander, Sicoob, Sicredi, Stone

**Requisição**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | arquivo PDF | sim | Extrato bancário em PDF |

**Exemplo com cURL**
```bash
curl -X POST https://sistemas-contajur.up.railway.app/api/extratos/processar \
  -F "file=@extrato_abril.pdf"
```

**Exemplo com Python**
```python
import requests

with open("extrato_abril.pdf", "rb") as f:
    response = requests.post(
        "https://sistemas-contajur.up.railway.app/api/extratos/processar",
        files={"file": f}
    )

data = response.json()
print(data["banco"])        # "Sicoob1"
print(data["transacoes"])   # lista de transações
```

**Resposta de sucesso (200)**
```json
{
  "success": true,
  "banco": "Sicoob1",
  "filename": "extrato_abril.pdf",
  "transacoes": [
    {
      "data": "01/04/2025",
      "descricao": "TRANSFERÊNCIA RECEBIDA PIX",
      "valor": "1.234,56",
      "tipo": "C"
    },
    {
      "data": "02/04/2025",
      "descricao": "PAGAMENTO FORNECEDOR",
      "valor": "500,00",
      "tipo": "D"
    }
  ]
}
```

> `tipo`: **C** = Crédito, **D** = Débito

**Respostas de erro**

| Status | Motivo |
|--------|--------|
| `400` | Nenhum arquivo enviado ou extensão inválida |
| `422` | Banco não identificado ou nenhuma transação encontrada |
| `500` | Erro interno ao processar o PDF |

```json
{
  "success": false,
  "error": "Banco não identificado"
}
```

---

### `POST /api/boletos/processar`

Reconcilia boletos pagos comparando o extrato bancário com a lista de boletos emitidos.

**Requisição**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `csv1` | arquivo CSV | sim | Extrato bancário exportado pelo sistema (separador `;`, sem cabeçalho, colunas: `data;descrição;valor;tipo`) |
| `csv2` | arquivo CSV | sim | Lista de boletos emitidos (separador `;`, com 2 linhas de cabeçalho, deve conter a coluna `Valor parcela`) |

**Exemplo com cURL**
```bash
curl -X POST https://sistemas-contajur.up.railway.app/api/boletos/processar \
  -F "csv1=@extrato_banco.csv" \
  -F "csv2=@boletos_emitidos.csv"
```

**Exemplo com Python**
```python
import requests

with open("extrato_banco.csv", "rb") as f1, open("boletos_emitidos.csv", "rb") as f2:
    response = requests.post(
        "https://sistemas-contajur.up.railway.app/api/boletos/processar",
        files={
            "csv1": f1,
            "csv2": f2
        }
    )

data = response.json()
print(f"Boletos pagos encontrados: {data['total_correspondencias']}")
print(f"Boletos sem correspondência: {data['total_sem_correspondencia']}")
```

**Resposta de sucesso (200)**
```json
{
  "success": true,
  "total_correspondencias": 3,
  "total_sem_correspondencia": 1,
  "correspondencias": [
    {
      "data": "05/04/2025",
      "descricao": "DÉB. TIT. COBRANÇA",
      "valor": 1500.00
    },
    {
      "data": "10/04/2025",
      "descricao": "DÉB.TIT.COB.EFETIV",
      "valor": 800.50
    }
  ],
  "boletos_sem_correspondencia": [
    {
      "data": "15/04/2025",
      "descricao": "DÉB. TIT. COBRANÇA",
      "valor": 2200.00
    }
  ]
}
```

**Respostas de erro**

| Status | Motivo |
|--------|--------|
| `400` | Um ou ambos os arquivos não foram enviados |
| `422` | Coluna `Valor parcela` não encontrada no CSV2 |
| `500` | Erro interno ao processar os arquivos |

```json
{
  "success": false,
  "error": "Coluna 'Valor parcela' não encontrada no CSV2."
}
```

---

## Formato dos CSVs de boletos

**csv1 — Extrato bancário** (gerado pelo sistema de extratos):
```
01/04/2025;PIX RECEBIDO EMPRESA X;1500,00;C
05/04/2025;DÉB. TIT. COBRANÇA;1500,00;D
10/04/2025;DÉB.TIT.COB.EFETIV;800,50;D
```

**csv2 — Boletos emitidos** (exportado do sistema de cobranças):
```
Nome da Empresa;
Relatório de Boletos;
Vencimento;Sacado;Valor parcela;Status
01/04/2025;Cliente A;1.500,00;Pago
08/04/2025;Cliente B;800,50;Pago
12/04/2025;Cliente C;2.200,00;Em aberto
```
