FROM python:3.9-slim

WORKDIR /app

# REMOVED: Dependency installation during build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate gRPC stubs for clients (from unified root protos)
COPY protos/stt.proto ./stt.proto
COPY protos/llm.proto ./llm.proto
COPY protos/tts.proto ./tts.proto
RUN python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  stt.proto llm.proto tts.proto

# COPY models ./models
COPY app.py .

# Expor porta para a API
EXPOSE 7000

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7000"]
