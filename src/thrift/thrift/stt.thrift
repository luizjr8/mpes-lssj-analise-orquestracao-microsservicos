namespace py mpes.stt

struct TranscribeReply {
  1: string text,
  2: string error
}

service STTService {
  TranscribeReply Transcribe(1: binary audio, 2: string filename, 3: string content_type)
}
