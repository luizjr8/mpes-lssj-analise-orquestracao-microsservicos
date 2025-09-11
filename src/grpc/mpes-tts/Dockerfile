# Build stage
FROM python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies for compiling llama-cpp-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    wget gnupg2 ca-certificates \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate gRPC stubs for TTS from root protos
COPY protos/tts.proto ./tts.proto
RUN python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  tts.proto

COPY app.py ./

# Expose gRPC port
EXPOSE 50053

CMD ["python", "app.py"]
