# File: LLM Thrift server
import logging
import os
import hashlib
import json
from functools import wraps

import thriftpy2
from thriftpy2.rpc import make_server
import torch
from llama_cpp import Llama

logger = logging.getLogger("mpes-llm-thrift")
logging.basicConfig(level=logging.INFO)

MODEL_PATH = "./models/Meta-Llama-3-8B-Instruct.Q5_K_S.gguf"
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

# Load Thrift IDL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LLM_THRIFT = thriftpy2.load(os.path.join(BASE_DIR, "thrift", "llm.thrift"), module_name="llm_thrift")

def _generate_cache_key(req) -> str:
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
        from asyncio import get_event_loop, iscoroutine
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
async def _cached_generate(cache_key: str, req) -> str:
    if model is None:
        raise RuntimeError("Model not loaded")
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
    text = out["choices"][0]["message"]["content"].strip()
    return text

class LLMServiceHandler:
    def Generate(self, req):
        try:
            cache_key = _generate_cache_key(req)
            import asyncio
            generated = asyncio.run(_cached_generate(cache_key, req))
            return LLM_THRIFT.GenReply(generated=generated, error="")
        except Exception as e:
            logger.exception("Generation error")
            return LLM_THRIFT.GenReply(generated="", error=str(e))

def serve() -> None:
    host = os.getenv("LLM_THRIFT_HOST", "0.0.0.0")
    port = int(os.getenv("LLM_THRIFT_PORT", "50052"))
    logger.info(f"Starting LLM Thrift server on {host}:{port}")
    server = make_server(LLM_THRIFT.LLMService, LLMServiceHandler(), host, port, client_timeout=0)
    server.serve()

if __name__ == "__main__":
    serve()
