# Build (Dependências)
FROM python:3.9-slim AS builder

# Criar e definir diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --user --no-cache-dir -r requirements.txt

# Generate gRPC stubs during build (to vendor into final image) from unified root protos
COPY ./protos/stt.proto ./stt.proto
RUN python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  stt.proto

# Binário estático do ffmpeg
COPY --from=mwader/static-ffmpeg:latest /ffmpeg /usr/local/bin/ffmpeg

WORKDIR /app

COPY app.py ./

# Expor porta para gRPC
EXPOSE 50051

# Comando para iniciar a aplicação
ENV PATH="/root/.local/bin:${PATH}"
CMD ["python", "app.py"]