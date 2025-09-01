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
    
WORKDIR /app

# REMOVED: Dependency installation during build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY models ./models
COPY app.py .

# Expor porta para a API
EXPOSE 8002

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
