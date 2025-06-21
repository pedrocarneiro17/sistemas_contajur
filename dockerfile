FROM python:3.11-slim-bullseye

# Evitar interações e manter ambiente limpo
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
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

# Diretório da aplicação
WORKDIR /app

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copia os arquivos do projeto
COPY . .

# Porta para exposição
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "main.py"]
