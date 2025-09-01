import asyncio
import logging
import os
import tempfile
from concurrent import futures

import grpc
import whisper

from google.protobuf import empty_pb2

import stt_pb2
import stt_pb2_grpc

logger = logging.getLogger("mpes-stt-grpc")
logging.basicConfig(level=logging.INFO)

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
MODEL = whisper.load_model(MODEL_SIZE, download_root="./models/")

class STTService(stt_pb2_grpc.STTServiceServicer):
    async def Transcribe(self, request: stt_pb2.TranscribeRequest, context: grpc.aio.ServicerContext) -> stt_pb2.TranscribeReply:
        try:
            suffix = os.path.splitext(request.filename)[1] if request.filename else ""
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
                tmp.write(request.audio)
                tmp.flush()
                logger.info(f"Transcribing audio via gRPC, filename={request.filename}")
                result = MODEL.transcribe(tmp.name, language="pt")
                text = result.get("text", "")
                return stt_pb2.TranscribeReply(text=text, error="")
        except Exception as e:
            logger.exception("Transcription error")
            return stt_pb2.TranscribeReply(text="", error=str(e))

async def serve() -> None:
    server = grpc.aio.server(options=[
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ("grpc.max_send_message_length", 64 * 1024 * 1024),
    ])
    stt_pb2_grpc.add_STTServiceServicer_to_server(STTService(), server)
    port = os.getenv("STT_GRPC_PORT", "50051")
    server.add_insecure_port(f"0.0.0.0:{port}")
    logger.info(f"Starting STT gRPC server on :{port}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
