import pandas as pd
import re
from typing import BinaryIO


def _clean_float(value) -> float:
    try:
        s = re.sub(r'[^\d,.]', '', str(value)).strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '')
        s = s.replace(',', '.')
        return float(s)
    except (ValueError, TypeError):
        return 0.0


PALAVRAS_CHAVE_BOLETO = [
    'DÉB. TIT. COBRANÇA', 'DÉB.TIT.COB.EFETIV', 'DÉB.TIT.COMPE.EFETI',
    'SIPAG FORNECEDORES', 'PAGTO ELETRON', 'boleto', 'Boleto', 'BOLETO',
    'DÉB.PGTO.BOLETO INT'
]


def processar_boletos(file1: BinaryIO, file2: BinaryIO) -> dict:
    """
    Reconcilia dois CSVs de boletos.

    Parâmetros:
        file1: CSV do extrato bancário (colunas: data;descrição;valor;tipo)
        file2: CSV de boletos emitidos (skiprows=2, coluna 'Valor parcela')

    Retorno:
        {
            "correspondencias": [{"data": str, "descricao": str, "valor": float}],
            "boletos_sem_correspondencia": [{"data": str, "descricao": str, "valor": float}],
            "total_correspondencias": int,
            "total_sem_correspondencia": int
        }
    """
    def _read_bytes(f: BinaryIO) -> bytes:
        content = f.read()
        return content

    content1 = _read_bytes(file1)
    try:
        text1 = content1.decode('utf-8')
    except UnicodeDecodeError:
        text1 = content1.decode('latin1')

    content2 = _read_bytes(file2)
    try:
        text2 = content2.decode('utf-8')
    except UnicodeDecodeError:
        text2 = content2.decode('latin1')

    import io
    df1 = pd.read_csv(io.StringIO(text1), header=None, sep=';', on_bad_lines='warn')

    try:
        df2 = pd.read_csv(io.StringIO(text2), skiprows=2, sep=';', on_bad_lines='skip')
    except pd.errors.ParserError:
        df2 = pd.read_csv(io.StringIO(text2), skiprows=2, sep=',', on_bad_lines='skip')

    if 'Valor parcela' not in df2.columns:
        raise ValueError("Coluna 'Valor parcela' não encontrada no CSV2.")

    df1_filtered = df1[df1.iloc[:, 3] == 'D'].copy()
    df1_filtered['date'] = pd.to_datetime(df1_filtered.iloc[:, 0], format='%d/%m/%Y', errors='coerce')
    df1_filtered['value'] = df1_filtered.iloc[:, 2].apply(_clean_float)

    matches_dict = dict(zip(
        df1_filtered['value'],
        zip(df1_filtered['date'], df1_filtered.iloc[:, 1])
    ))

    df2_filtered = df2[df2['Valor parcela'].apply(lambda v: _clean_float(v) != 0.0 or str(v).strip() == '0')].copy()
    df2_filtered['value'] = df2_filtered['Valor parcela'].apply(_clean_float)

    correspondencias = []
    for _, row in df2_filtered.iterrows():
        value = row['value']
        if value in matches_dict:
            date, descricao = matches_dict[value]
            correspondencias.append({
                'data': date.strftime('%d/%m/%Y') if pd.notna(date) else 'Data Inválida',
                'descricao': str(descricao),
                'valor': round(value, 2)
            })

    df1_boletos = df1_filtered[
        df1_filtered.iloc[:, 1].astype(str).str.contains(
            '|'.join(PALAVRAS_CHAVE_BOLETO), case=False, na=False
        )
    ]
    df2_values = set(df2_filtered['value'].values)

    boletos_sem_correspondencia = []
    for _, row in df1_boletos.iterrows():
        value = row['value']
        if value not in df2_values:
            boletos_sem_correspondencia.append({
                'data': row['date'].strftime('%d/%m/%Y') if pd.notna(row['date']) else 'Data Inválida',
                'descricao': str(row.iloc[1]),
                'valor': round(value, 2)
            })

    return {
        'correspondencias': correspondencias,
        'boletos_sem_correspondencia': boletos_sem_correspondencia,
        'total_correspondencias': len(correspondencias),
        'total_sem_correspondencia': len(boletos_sem_correspondencia)
    }
