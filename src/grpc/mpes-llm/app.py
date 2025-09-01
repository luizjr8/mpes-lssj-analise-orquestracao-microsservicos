# File: llama_small_app.py
import asyncio
import logging
import os
import hashlib
import json
from datetime import datetime
from functools import wraps

import grpc
import torch
from llama_cpp import Llama

import llm_pb2
import llm_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mpes-llm-grpc")

MODEL_PATH = "./models/Meta-Llama-3-8B-Instruct-Q5_K_S.gguf"
CTX = 512
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Device: {DEVICE}")
try:
    logger.info(f"Loading LLaMA from {MODEL_PATH}")
    model = Llama(model_path=MODEL_PATH, n_ctx=CTX, device=DEVICE, n_gpu_layers=-1)
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    model = None

def _generate_cache_key(req: llm_pb2.GenRequest) -> str:
    key_data = {
        "prompt": req.prompt,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "top_k": req.top_k,
        "repeat_penalty": req.repeat_penalty,
        "presence_penalty": req.presence_penalty,
        "frequency_penalty": req.frequency_penalty,
    }
    return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

def async_lru_cache(maxsize: int = 1000):
    cache = {}
    queue = []

    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            key = str((args, frozenset(kwargs.items())))
            if key in cache:
                return cache[key]
            result = await fn(*args, **kwargs)
            if len(queue) >= maxsize:
                old_key = queue.pop(0)
                cache.pop(old_key, None)
            cache[key] = result
            queue.append(key)
            return result

        return wrapper
    return decorator

@async_lru_cache(maxsize=1000)
async def _cached_generate(cache_key: str, req: llm_pb2.GenRequest) -> str:
    if model is None:
        raise RuntimeError("Model not loaded")

    max_retries = 3
    text = ""
    for attempt in range(max_retries):
        messages = [
            {"role": "system", "content": """
            Você é um assistente financeiro. 
            Responda apenas com informações e conselhos estritamente relacionados ao contexto financeiro solicitado. 
            Você falará sempre em português brasileiro, usando linguagem clara e simples, com números exatos e sem arredondamentos.
            Apenas responda. Não faça novas perguntas. Responda em um único parágrafo, com até 50 palavras.
            
            """.strip()},
            {"role": "user", "content": req.prompt},
        ]
        out = model.create_chat_completion(
            messages=messages,
            max_tokens=req.max_tokens or 256,
            temperature=req.temperature or 0.7,
            top_p=req.top_p or 0.9,
            top_k=req.top_k or 40,
            repeat_penalty=req.repeat_penalty or 1.1,
            presence_penalty=req.presence_penalty or 0.0,
            frequency_penalty=req.frequency_penalty or 0.0,
        )
        text = out["choices"][0]["message"]['content'].strip()
        logger.info(f"Generated response (attempt {attempt+1}): {text[:100]}...")
        if text:
            break
        logger.warning(f"Empty response, retrying {attempt+1}/{max_retries}")

    if not text:
        raise RuntimeError("Empty response from model after retries")
    return text

class LLMService(llm_pb2_grpc.LLMServiceServicer):
    async def Generate(self, request: llm_pb2.GenRequest, context: grpc.aio.ServicerContext) -> llm_pb2.GenReply:
        try:
            cache_key = _generate_cache_key(request)
            generated = await _cached_generate(cache_key, request)
            return llm_pb2.GenReply(generated=generated, error="")
        except Exception as e:
            logger.exception("Generation error")
            return llm_pb2.GenReply(generated="", error=str(e))

async def serve() -> None:
    server = grpc.aio.server(options=[
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
    ])
    llm_pb2_grpc.add_LLMServiceServicer_to_server(LLMService(), server)
    port = os.getenv("LLM_GRPC_PORT", "50052")
    server.add_insecure_port(f"0.0.0.0:{port}")
    logger.info(f"Starting LLM gRPC server on :{port}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
