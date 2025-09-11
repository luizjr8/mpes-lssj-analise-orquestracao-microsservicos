# Build stage
FROM python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies for compiling llama-cpp-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    wget gnupg2 ca-certificates \
    libopenblas-dev \
    libopenblas0 \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# adicionar repo da NVIDIA
RUN wget https://developer.download.nvidia.com/compute/cuda/13.0.1/local_installers/cuda-repo-debian12-13-0-local_13.0.1-580.82.07-1_amd64.deb \
    && dpkg -i cuda-repo-debian12-13-0-local_13.0.1-580.82.07-1_amd64.deb \
    && apt-key add /var/cuda-repo-debian12-13-0-local/7fa2af80.pub \
    && apt-get update \
    && apt-get -y install cuda-toolkit-13-0 \
    && rm cuda-repo-debian12-13-0-local_13.0.1-580.82.07-1_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# opcional: verificar
RUN nvcc --version

# Enable BLAS (OpenBLAS) for llama-cpp-python build
ENV CMAKE_ARGS="-DGGML_CUDA=ON -DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
ENV FORCE_CMAKE=1

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Generate gRPC stubs for LLM from root protos
COPY protos/llm.proto ./llm.proto
RUN python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  llm.proto

COPY app.py ./

ENV PATH="/root/.local/bin:${PATH}"

# Expose gRPC port
EXPOSE 50052

CMD ["python", "app.py"]