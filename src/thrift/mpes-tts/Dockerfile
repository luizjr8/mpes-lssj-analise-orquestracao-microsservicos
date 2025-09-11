# Build stage
FROM python:3.9-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Generate gRPC stubs for TTS from root protos
COPY protos/tts.proto ./tts.proto
RUN /root/.local/bin/python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  tts.proto

# Final stage
FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/tts.proto /app/tts.proto
COPY --from=builder /app/tts_pb2.py /app/tts_pb2.py
COPY --from=builder /app/tts_pb2_grpc.py /app/tts_pb2_grpc.py
COPY app.py ./

ENV PATH="/root/.local/bin:${PATH}"

# Expose gRPC port
EXPOSE 50053

CMD ["python", "app.py"]
