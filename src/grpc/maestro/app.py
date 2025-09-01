from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import io
import os
import logging
import asyncio
import grpc

from stt_pb2 import TranscribeRequest
from stt_pb2_grpc import STTServiceStub
from llm_pb2 import GenRequest
from llm_pb2_grpc import LLMServiceStub
from tts_pb2 import SynthRequest
from tts_pb2_grpc import TTSServiceStub

# Logger setup
logger = logging.getLogger("mpes-maestro")
logging.basicConfig(level=logging.INFO)

# FastAPI app
app = FastAPI(title="mpes-maestro")

# Service addrs (configurable via env vars)
STT_GRPC_ADDR = os.getenv("STT_GRPC_ADDR", "localhost:50051")
LLM_GRPC_ADDR = os.getenv("LLM_GRPC_ADDR", "localhost:50052")
TTS_GRPC_ADDR = os.getenv("TTS_GRPC_ADDR", "localhost:50053")

# HTTPX client limits and timeouts (tune via env vars)
MAX_CONNECTIONS = int(os.getenv("MAESTRO_MAX_CONNECTIONS", "1000"))
MAX_KEEPALIVE = int(os.getenv("MAESTRO_MAX_KEEPALIVE", "200"))
CONCURRENCY_LIMIT = int(os.getenv("MAESTRO_MAX_CONCURRENCY", "1000"))

@app.on_event("startup")
async def on_startup():    
    # Concurrency guard to avoid too many in-flight requests
    app.state.sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    # gRPC channels and stubs
    app.state.stt_channel = grpc.aio.insecure_channel(STT_GRPC_ADDR, options=[
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
    ])
    app.state.stt_stub = STTServiceStub(app.state.stt_channel)
    app.state.llm_channel = grpc.aio.insecure_channel(LLM_GRPC_ADDR, options=[
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
    ])
    app.state.llm_stub = LLMServiceStub(app.state.llm_channel)
    app.state.tts_channel = grpc.aio.insecure_channel(TTS_GRPC_ADDR, options=[
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
    ])
    app.state.tts_stub = TTSServiceStub(app.state.tts_channel)

@app.on_event("shutdown")
async def on_shutdown():
    # Close gRPC channel
    await app.state.stt_channel.close()
    await app.state.llm_channel.close()
    await app.state.tts_channel.close()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/assist")
async def assist(file: UploadFile = File(...)):
    #log
    logger.info(f"Received file: {file.filename}")    
    sem: asyncio.Semaphore = app.state.sem
    async with sem:
        try:
            content = await file.read()
            # Log
            logger.info(f"STT request: {file.filename}")            
            # 1. STT via gRPC
            stub: STTServiceStub = app.state.stt_stub
            stt_reply = await stub.Transcribe(TranscribeRequest(
                audio=content,
                filename=file.filename or "audio.wav",
                content_type=file.content_type or "audio/wav",
            ))
            if getattr(stt_reply, "error", ""):
                raise HTTPException(status_code=502, detail=f"STT error: {stt_reply.error}")
            stt_text = stt_reply.text
            logger.info(f"STT result: {stt_text}")

            # 2. LLM via gRPC
            logger.info(f"LLM request: {stt_text}")
            llm_stub: LLMServiceStub = app.state.llm_stub
            llm_reply = await llm_stub.Generate(GenRequest(prompt=stt_text))
            if getattr(llm_reply, "error", ""):
                raise HTTPException(status_code=502, detail=f"LLM error: {llm_reply.error}")
            generated = llm_reply.generated
            logger.info(f"LLM result: {generated}")

            # 3. TTS via gRPC
            tts_stub: TTSServiceStub = app.state.tts_stub
            tts_reply = await tts_stub.Synthesize(SynthRequest(text=generated))
            if getattr(tts_reply, "error", ""):
                raise HTTPException(status_code=502, detail=f"TTS error: {tts_reply.error}")
            audio_bytes = tts_reply.audio
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=502, detail=str(e))

    # Stream back WAV audio
    # return {"text": generated}
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)