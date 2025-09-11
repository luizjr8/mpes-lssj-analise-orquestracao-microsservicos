# Build stage
FROM python:3.9-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Generate gRPC stubs for LLM from root protos
COPY protos/llm.proto ./llm.proto
RUN /root/.local/bin/python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  llm.proto

# Final stage
FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/llm.proto /app/llm.proto
COPY --from=builder /app/llm_pb2.py /app/llm_pb2.py
COPY --from=builder /app/llm_pb2_grpc.py /app/llm_pb2_grpc.py
COPY app.py ./

ENV PATH="/root/.local/bin:${PATH}"

# Expose gRPC port
EXPOSE 50052

CMD ["python", "app.py"]