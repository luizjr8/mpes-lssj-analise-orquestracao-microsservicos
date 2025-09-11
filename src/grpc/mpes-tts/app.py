import asyncio
import logging
import os
import tempfile
from pathlib import Path

import grpc
from TTS.api import TTS as CoquiTTS

import tts_pb2
import tts_pb2_grpc
import hashlib
import json
from functools import wraps

logger = logging.getLogger("mpes-tts-grpc")
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

class TTSService(tts_pb2_grpc.TTSServiceServicer):
    async def Synthesize(self, request: tts_pb2.SynthRequest, context: grpc.aio.ServicerContext) -> tts_pb2.SynthReply:
        try:
            text = (request.text or "").strip()
            if not text:
                return tts_pb2.SynthReply(audio=b"", error="Empty text provided")

            if tts is None:
                return tts_pb2.SynthReply(audio=b"", error="TTS model not loaded")
            # Cache-aware synthesis
            cache_key = _generate_cache_key(text)
            data = await _cached_synthesize(cache_key, text)
            return tts_pb2.SynthReply(audio=data, error="")
        except Exception as e:
            logger.exception("Synthesis error")
            return tts_pb2.SynthReply(audio=b"", error=str(e))

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

async def serve() -> None:
    server = grpc.aio.server(options=[
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
    ])
    tts_pb2_grpc.add_TTSServiceServicer_to_server(TTSService(), server)
    port = os.getenv("TTS_GRPC_PORT", "50053")
    server.add_insecure_port(f"0.0.0.0:{port}")
    logger.info(f"Starting TTS gRPC server on :{port}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
