import logging
import os
import tempfile
import threading

import whisper
import thriftpy2
from thriftpy2.rpc import make_server
import torch

logger = logging.getLogger("mpes-stt-thrift")
logging.basicConfig(level=logging.INFO)

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
MODEL = whisper.load_model(MODEL_SIZE, download_root="./models/")
TRANSCRIBE_LOCK = threading.Lock()

# Load Thrift IDL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STT_THRIFT = thriftpy2.load(os.path.join(BASE_DIR, "thrift", "stt.thrift"), module_name="stt_thrift")

class STTServiceHandler:
    def Transcribe(self, audio: bytes, filename: str, content_type: str):
        try:
            suffix = os.path.splitext(filename)[1] if filename else ""
            # Use a regular file inside a TemporaryDirectory to avoid file locks
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = os.path.join(tmpdir, f"audio{suffix or '.wav'}")
                with open(tmp_path, "wb") as f:
                    f.write(audio)
                logger.info(f"Transcribing audio via Thrift, filename={filename}")
                # Ensure single-threaded access to shared Whisper model and disable fp16 on CPU
                with TRANSCRIBE_LOCK:
                    with torch.no_grad():
                        result = MODEL.transcribe(
                            tmp_path,
                            language="pt",
                            fp16=torch.cuda.is_available(),
                        )
                text = result.get("text", "")
                return STT_THRIFT.TranscribeReply(text=text, error="")
        except Exception as e:
            logger.exception("Transcription error")
            return STT_THRIFT.TranscribeReply(text="", error=str(e))

def serve() -> None:
    host = os.getenv("STT_THRIFT_HOST", "0.0.0.0")
    port = int(os.getenv("STT_THRIFT_PORT", os.getenv("STT_GRPC_PORT", "50051")))
    logger.info(f"Starting STT Thrift server on {host}:{port}")
    server = make_server(STT_THRIFT.STTService, STTServiceHandler(), host, port, client_timeout=0)
    server.serve()

if __name__ == "__main__":
    serve()
