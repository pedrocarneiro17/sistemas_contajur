# Use Python 3.11 slim (menor e mais seguro)
FROM python:3.11-slim-bullseye

# Evita mensagens interativas na instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências do sistema necessárias para pandas, PyMuPDF, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Define o diretório raiz da aplicação dentro do container
WORKDIR /app

# Copia o arquivo de dependências para instalar
COPY requirements.txt .

# Atualiza pip e instala dependências do Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código para dentro do container
COPY . .

# Expõe a porta da aplicação (ajuste se precisar)
EXPOSE 5000

# Comando para rodar o app - usando o módulo python para respeitar imports relativos
CMD ["python", "-m", "home.main"]
