from .sicoob import process as process_sicoob
from .sicoob2 import process as process_sicoob2
from .sicoob3 import process as process_sicoob3
from .itau import process as process_itau
from .itau2 import process as process_itau2
from .itau3 import process as process_itau3
from .caixa import process as process_caixa
from .inter import process as process_inter
from .nubank import process as process_nubank
from .bradesco import process as process_bradesco
from .santander1 import process as process_santander1
from .santander2 import process as process_santander2
from .sicredi import process as process_sicredi
from .pagbank import process as process_pagbank
from .stone import process as process_stone
from .bancobrasil1 import process as process_bancobrasil1
from .bancobrasil2 import process as process_bancobrasil2
from .ifood import process as process_ifood
from .asaas import process as process_asaas
from .cora import process as process_cora
from .safra import process as process_safra
from .infinitepay import process as process_infinitepay
from .efi1 import process as process_efi1
from .efi2 import process as process_efi2
from .mercadopago import process as process_mercadopago

BANK_PROCESSORS = {
    "Sicoob1": process_sicoob,
    "Sicoob2": process_sicoob2,
    "Sicoob3": process_sicoob3,
    "Itaú": process_itau,
    "Itaú2": process_itau2,
    "Itaú3": process_itau3,
    "Caixa": process_caixa,
    "Banco Inter": process_inter,
    "Nubank": process_nubank,
    "Bradesco": process_bradesco,
    "Santander1": process_santander1,
    "Santander2": process_santander2,
    "Sicredi": process_sicredi,
    "PagBank": process_pagbank,
    "Stone": process_stone,
    "Banco do Brasil1": process_bancobrasil1,
    "Banco do Brasil2": process_bancobrasil2,
    "iFood": process_ifood,
    "Asaas": process_asaas,
    "Cora": process_cora,
    "Safra": process_safra,
    "InfinitePay": process_infinitepay,
    "Efi1": process_efi1,
    "Efi2": process_efi2,
    "Mercado Pago": process_mercadopago
}

def get_processor(bank):
    
    processor = BANK_PROCESSORS.get(bank)
    if not processor:
        raise ValueError(f"Banco não suportado: {bank}")
    return processor