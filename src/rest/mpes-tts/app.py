from fastapi import FastAPI, Response
from pydantic import BaseModel
from pathlib import Path
import tempfile
from TTS.api import TTS

app = FastAPI()

# carrega modelo pré-treinado (troque para outro se quiser mais rápido ou pt-BR específico)
# veja lista: https://tts.readthedocs.io/en/latest/models.html
tts = TTS("tts_models/pt/cv/vits")

class SynthesisRequest(BaseModel):
    text: str

@app.post("/synthesize")
async def synthesize(req: SynthesisRequest) -> Response:
    if not req.text.strip():
        return Response(content="Empty text provided", status_code=400)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "out.wav"
        tts.tts_to_file(text=req.text, file_path=out_path)
        data = out_path.read_bytes()

    return Response(content=data, media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8002)
