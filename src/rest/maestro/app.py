from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import io
import os
import logging
import asyncio

# Logger setup
logger = logging.getLogger("mpes-maestro")
logging.basicConfig(level=logging.INFO)

# FastAPI app
app = FastAPI(title="mpes-maestro")

# Service URLs (configurable via env vars)
STT_URL = os.getenv("STT_URL", "http://mpes-stt:8000/transcribe")
LLM_URL = os.getenv("LLM_URL", "http://mpes-llm:8001/generate")
TTS_URL = os.getenv("TTS_URL", "http://mpes-tts:8002/synthesize")

# HTTPX client limits and timeouts (tune via env vars)
MAX_CONNECTIONS = int(os.getenv("MAESTRO_MAX_CONNECTIONS", "100"))
MAX_KEEPALIVE = int(os.getenv("MAESTRO_MAX_KEEPALIVE", "20"))
CONCURRENCY_LIMIT = int(os.getenv("MAESTRO_MAX_CONCURRENCY", "50"))

# Separate timeouts per phase; read can be long for TTS
HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=240.0, write=60.0, pool=10.0)
HTTP_LIMITS = httpx.Limits(max_connections=MAX_CONNECTIONS, max_keepalive_connections=MAX_KEEPALIVE)

@app.on_event("startup")
async def on_startup():
    # Shared AsyncClient to reuse connections under load
    app.state.http_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS)
    # Concurrency guard to avoid too many in-flight requests
    app.state.sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

@app.on_event("shutdown")
async def on_shutdown():
    client: httpx.AsyncClient = app.state.http_client
    await client.aclose()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/assist")
async def assist(file: UploadFile = File(...)):
    sem: asyncio.Semaphore = app.state.sem
    async with sem:
        try:
            content = await file.read()
            client: httpx.AsyncClient = app.state.http_client
            # 1. STT
            files = {"file": (file.filename, content, file.content_type)}
            params = {"forward": False}
            stt_resp = await client.post(STT_URL, files=files, params=params)
            stt_resp.raise_for_status()
            stt_text = stt_resp.json().get("text", "")
            logger.info(f"STT result: {stt_text}")

            # 2. LLM
            llm_resp = await client.post(LLM_URL, json={"prompt": stt_text})
            llm_resp.raise_for_status()
            generated = llm_resp.json().get("generated", "")
            logger.info(f"LLM result: {generated}")

            # 3. TTS
            tts_resp = await client.post(TTS_URL, json={"text": generated})
            tts_resp.raise_for_status()
            audio_bytes = tts_resp.content
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=502, detail=str(e))
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    # Stream back WAV audio
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)