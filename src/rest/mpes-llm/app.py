# File: llama_small_app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from llama_cpp import Llama
from datetime import datetime
import torch
import hashlib
from functools import wraps
import json
import asyncio

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mpes-llm")

# FastAPI
app = FastAPI(title="mpes-llm")

# modelo
MODEL_PATH = "./models/Meta-Llama-3-8B-Instruct.Q5_K_S.gguf"
CTX = 512
PRE_PROMPT = ""
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

try:
		logger.info(f"Loading LLaMA small from {MODEL_PATH}")
		model = Llama(model_path=MODEL_PATH, n_ctx=CTX, device=DEVICE, n_gpu_layers=-1)
		logger.info("Model loaded successfully")
except Exception as e:
		logger.error(f"Failed to load model: {e}")
		model = None

class GenRequest(BaseModel):
    prompt: str
    max_tokens: int = 256	
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

class GenResponse(BaseModel):
		prompt: str
		generated: str

@app.get("/health")
async def health():
		if model is None:
				raise HTTPException(500, "Model not loaded")
		return {"status": "healthy"}

def _generate_cache_key(req: GenRequest) -> str:
    """Generate a unique cache key based on the request parameters."""
    key_data = {
        "prompt": req.prompt,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "top_k": req.top_k,
        "repeat_penalty": req.repeat_penalty,
        "presence_penalty": req.presence_penalty,
        "frequency_penalty": req.frequency_penalty
    }
    # Convert to JSON string and hash it for a fixed-length key
    return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

def async_lru_cache(maxsize: int = 1000):
    """Simple async LRU cache decorator."""
    cache = {}
    queue = []
    
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            key = str((args, frozenset(kwargs.items())))
            
            if key in cache:
                logger.info(f"Cache hit for prompt: {args[1].prompt[:50]}...")
                return cache[key]
                
            result = await fn(*args, **kwargs)
            
            if len(queue) >= maxsize:
                # Remove the oldest item
                old_key = queue.pop(0)
                cache.pop(old_key, None)
                
            cache[key] = result
            queue.append(key)
            return result
            
        return wrapper
    return decorator

@async_lru_cache(maxsize=1000)  # Cache up to 1000 unique requests
async def _cached_generate(cache_key: str, req: GenRequest) -> dict:
    """Generate response with retry logic, called by the cache wrapper."""
    if model is None:
        raise HTTPException(500, "Model not loaded")
    
    max_retries = 3
    text = ""
    for attempt in range(max_retries):
        current_date = datetime.now().strftime("%d %B %Y")
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
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
            top_k=req.top_k,
            repeat_penalty=req.repeat_penalty,
            presence_penalty=req.presence_penalty,
            frequency_penalty=req.frequency_penalty
        )
        text = out["choices"][0]["message"]['content'].strip()
        logger.info(f"Generated response (attempt {attempt+1}): {text[:100]}...")
        if text:
            break
        logger.warning(f"Empty response, retrying {attempt+1}/{max_retries}")
    
    if not text:
        raise HTTPException(502, "Empty response from model after retries")
    
    return {"prompt": req.prompt, "generated": text}

@app.post("/generate", response_model=GenResponse)
async def generate(req: GenRequest):
    """Generate a response with caching support."""
    try:
        cache_key = _generate_cache_key(req)
        logger.info(f"Cache key: {cache_key}")
        return await _cached_generate(cache_key, req)
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
		import uvicorn
		uvicorn.run(app, host="0.0.0.0", port=8001)
