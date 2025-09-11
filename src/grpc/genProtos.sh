#!/usr/bin/env bash
set -e

# Run from repo root: ./genProtos.sh

# Install tools (ignore errors if already installed)
python -m pip install --user grpcio-tools protobuf >/dev/null 2>&1 || true

# Ensure output dirs exist
mkdir -p mpes-stt mpes-llm mpes-tts maestro

echo "[GEN] STT stubs -> mpes-stt, maestro"
python -m grpc_tools.protoc -I protos \
  --python_out=mpes-stt \
  --grpc_python_out=mpes-stt \
  protos/stt.proto
python -m grpc_tools.protoc -I protos \
  --python_out=maestro \
  --grpc_python_out=maestro \
  protos/stt.proto

echo "[GEN] LLM stubs -> mpes-llm, maestro"
python -m grpc_tools.protoc -I protos \
  --python_out=mpes-llm \
  --grpc_python_out=mpes-llm \
  protos/llm.proto
python -m grpc_tools.protoc -I protos \
  --python_out=maestro \
  --grpc_python_out=maestro \
  protos/llm.proto

echo "[GEN] TTS stubs -> mpes-tts, maestro"
python -m grpc_tools.protoc -I protos \
  --python_out=mpes-tts \
  --grpc_python_out=mpes-tts \
  protos/tts.proto
python -m grpc_tools.protoc -I protos \
  --python_out=maestro \
  --grpc_python_out=maestro \
  protos/tts.proto

echo "[DONE] Generated stubs for STT, LLM, TTS in all services"
