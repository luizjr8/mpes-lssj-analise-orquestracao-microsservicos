from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import io
import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import thriftpy2
from thriftpy2.rpc import make_client

# Logger setup
logger = logging.getLogger("mpes-maestro")
logging.basicConfig(level=logging.INFO)

# FastAPI app
app = FastAPI(title="mpes-maestro")

# Service addrs (configurable via env vars)
STT_ADDR = os.getenv("STT_THRIFT_ADDR", os.getenv("STT_GRPC_ADDR", "localhost:50051"))
LLM_ADDR = os.getenv("LLM_THRIFT_ADDR", os.getenv("LLM_GRPC_ADDR", "localhost:50052"))
TTS_ADDR = os.getenv("TTS_THRIFT_ADDR", os.getenv("TTS_GRPC_ADDR", "localhost:50053"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STT_THRIFT = thriftpy2.load(os.path.join(BASE_DIR, "thrift", "stt.thrift"), module_name="stt_thrift")
LLM_THRIFT = thriftpy2.load(os.path.join(BASE_DIR, "thrift", "llm.thrift"), module_name="llm_thrift")
TTS_THRIFT = thriftpy2.load(os.path.join(BASE_DIR, "thrift", "tts.thrift"), module_name="tts_thrift")

def _parse_host_port(addr: str):
    host, port = addr.split(":", 1)
    return host, int(port)

# Concurrency config
CONCURRENCY_LIMIT = int(os.getenv("MAESTRO_MAX_CONCURRENCY", "100"))

@app.on_event("startup")
async def on_startup():    
    # Concurrency guard and worker pool (one thread per request up to limit)
    app.state.sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    app.state.executor = ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT)
    # Thrift clients (LLM/TTS persistent). STT will be per-request to avoid idle socket timeouts
    stt_host, stt_port = _parse_host_port(STT_ADDR)
    app.state.stt_host = stt_host
    app.state.stt_port = stt_port
    llm_host, llm_port = _parse_host_port(LLM_ADDR)
    app.state.llm_host = llm_host
    app.state.llm_port = llm_port
    tts_host, tts_port = _parse_host_port(TTS_ADDR)
    app.state.tts_host = tts_host
    app.state.tts_port = tts_port

@app.get("/health")
def health():
    return {"status": "healthy"}

def _run_pipeline(content: bytes, filename: str, content_type: str, state) -> bytes:
    # STT client per request
    stt_client = make_client(
        STT_THRIFT.STTService,
        state.stt_host,
        state.stt_port,
        timeout=300000,  # 5 min to tolerate long audios
    )
    try:
        stt_reply = stt_client.Transcribe(
            content,
            filename or "audio.wav",
            content_type or "audio/wav",
        )
    finally:
        try:
            stt_client.close()
        except Exception:
            pass
    if getattr(stt_reply, "error", ""):
        raise RuntimeError(f"STT error: {stt_reply.error}")
    stt_text = stt_reply.text
    logger.info(f"STT result: {stt_text}")

    # LLM client per request
    llm_client = make_client(
        LLM_THRIFT.LLMService,
        state.llm_host,
        state.llm_port,
        timeout=300000,  # 5 min
    )
    try:
        llm_req = LLM_THRIFT.GenRequest(
            prompt=stt_text,
            max_tokens=256,
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            presence_penalty=0.0,
            frequency_penalty=0.0,
        )
        llm_reply = llm_client.Generate(llm_req)
    finally:
        try:
            llm_client.close()
        except Exception:
            pass
    if getattr(llm_reply, "error", ""):
        raise RuntimeError(f"LLM error: {llm_reply.error}")
    generated = llm_reply.generated
    logger.info(f"LLM result: {generated}")

    # TTS client per request
    tts_client = make_client(
        TTS_THRIFT.TTSService,
        state.tts_host,
        state.tts_port,
        timeout=300000,  # 5 min
    )
    try:
        tts_reply = tts_client.Synthesize(generated)
    finally:
        try:
            tts_client.close()
        except Exception:
            pass
    if getattr(tts_reply, "error", ""):
        raise RuntimeError(f"TTS error: {tts_reply.error}")
    return tts_reply.audio


@app.post("/assist")
async def assist(file: UploadFile = File(...)):
    #log
    logger.info(f"Received file: {file.filename}")    
    sem: asyncio.Semaphore = app.state.sem
    async with sem:
        try:
            content = await file.read()
            logger.info(f"STT request: {file.filename}")
            loop = asyncio.get_running_loop()
            audio_bytes = await loop.run_in_executor(
                app.state.executor,
                _run_pipeline,
                content,
                file.filename or "audio.wav",
                file.content_type or "audio/wav",
                app.state,
            )
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=502, detail=str(e))

    # Stream back WAV audio
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)