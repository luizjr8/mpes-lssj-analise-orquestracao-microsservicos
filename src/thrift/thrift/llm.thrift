namespace py mpes.llm

struct GenRequest {
  1: string prompt,
  2: i32 max_tokens,
  3: double temperature,
  4: double top_p,
  5: i32 top_k,
  6: double repeat_penalty,
  7: double presence_penalty,
  8: double frequency_penalty
}

struct GenReply {
  1: string generated,
  2: string error
}

service LLMService {
  GenReply Generate(1: GenRequest req)
}
