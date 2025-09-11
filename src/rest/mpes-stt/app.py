from fastapi import FastAPI, UploadFile, File
import os
import tempfile
import hashlib
from functools import wraps
from typing import Callable
import asyncio

import whisper
import uvicorn
import logging

logger = logging.getLogger("mpes-stt")
logger.setLevel(logging.INFO)

app = FastAPI()

model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
model = whisper.load_model(model_size, download_root="./models/")

@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}

def _generate_audio_hash(content: bytes) -> str:
    """Generate a hash of the audio content for caching."""
    return hashlib.md5(content).hexdigest()

# Custom async LRU cache implementation
def async_lru_cache(maxsize: int = 128):
    cache = {}
    queue = []
    
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            key = str((args, frozenset(kwargs.items())))
            
            if key in cache:
                logger.info(f"Cache hit for key: {key}")
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

@async_lru_cache(maxsize=1000)  # Cache up to 1000 unique audio files
async def _cached_transcribe(audio_hash: str, audio_content: bytes, suffix: str) -> str:
    """Transcribe audio with caching support."""
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(audio_content)
        tmp.flush()
        logger.info(f"Transcribing audio (hash: {audio_hash})")
        result = model.transcribe(tmp.name, language="pt")
        return result.get("text", "")

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict:
    try:
        # Read the file content once
        content = await file.read()
        suffix = os.path.splitext(file.filename)[1]
        
        # Generate cache key and get/cache the transcription
        audio_hash = _generate_audio_hash(content)
        logger.info(f"Audio hash: {audio_hash}")
        
        # Get the transcription (from cache or generate)
        text = await _cached_transcribe(audio_hash, content, suffix)
        
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {"error": str(e), "text": ""}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
