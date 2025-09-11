import logging
import os
import tempfile
from pathlib import Path
import hashlib
import json
from functools import wraps

from TTS.api import TTS as CoquiTTS
import thriftpy2
from thriftpy2.rpc import make_server

logger = logging.getLogger("mpes-tts-thrift")
logging.basicConfig(level=logging.INFO)

# Load Coqui TTS model (Portuguese)
MODEL_ID = os.getenv("TTS_MODEL_ID", "tts_models/pt/cv/vits")
logger.info(f"Loading TTS model: {MODEL_ID}")
try:
    tts = CoquiTTS(MODEL_ID)
    logger.info("TTS model loaded")
except Exception as e:
    logger.error(f"Failed to load TTS model: {e}")
    tts = None

# Load Thrift IDL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T_THrift = thriftpy2.load(os.path.join(BASE_DIR, "thrift", "tts.thrift"), module_name="tts_thrift")

def _generate_cache_key(text: str) -> str:
    payload = {"text": text, "model": MODEL_ID}
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()

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
async def _cached_synthesize(cache_key: str, text: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "out.wav"
        tts.tts_to_file(text=text, file_path=out_path)
        data = out_path.read_bytes()
    return data

class TTSServiceHandler:
    def Synthesize(self, text: str):
        try:
            text = (text or "").strip()
            if not text:
                return T_THrift.SynthReply(audio=b"", error="Empty text provided")
            if tts is None:
                return T_THrift.SynthReply(audio=b"", error="TTS model not loaded")
            # Use cache (run async function synchronously)
            import asyncio
            cache_key = _generate_cache_key(text)
            data = asyncio.run(_cached_synthesize(cache_key, text))
            return T_THrift.SynthReply(audio=data, error="")
        except Exception as e:
            logger.exception("Synthesis error")
            return T_THrift.SynthReply(audio=b"", error=str(e))

def serve() -> None:
    host = os.getenv("TTS_THRIFT_HOST", "0.0.0.0")
    port = int(os.getenv("TTS_THRIFT_PORT", "50053"))
    logger.info(f"Starting TTS Thrift server on {host}:{port}")
    server = make_server(T_THrift.TTSService, TTSServiceHandler(), host, port)
    server.serve()

if __name__ == "__main__":
    serve()
