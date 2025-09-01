# Build (Dependências)
FROM python:3.9-slim AS builder

# Criar e definir diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --user --no-cache-dir -r requirements.txt

# Final (Imagem final)
FROM python:3.9-slim

# Binário estático do ffmpeg
COPY --from=mwader/static-ffmpeg:latest /ffmpeg /usr/local/bin/ffmpeg

WORKDIR /app

# Pacotes Python instalados do builder
COPY --from=builder /root/.local /root/.local

# Expor porta para a API
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]