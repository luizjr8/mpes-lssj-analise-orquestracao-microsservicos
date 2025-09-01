FROM python:3.9-slim

# Atualizar pacotes e instalar dependências
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    libopenblas-dev \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Add volume for persistence
VOLUME /app

# Criar o diretorio app
RUN mkdir /app
WORKDIR /app

# Instala os requerimentos
COPY requirements.txt .
RUN pip install --verbose --debug --no-cache-dir -r requirements.txt

# Copiar o arquivo app.py
COPY app.py .

# Expor porta para a API
EXPOSE 8001

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]