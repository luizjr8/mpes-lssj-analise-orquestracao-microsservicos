namespace py mpes.tts

struct SynthReply {
  1: binary audio,
  2: string error
}

service TTSService {
  SynthReply Synthesize(1: string text)
}
