#!/bin/bash

# Run each model on a separate tmux window
tmux new-session "uvicorn mpes-stt.app:app --reload --host 0.0.0.0 --port 8000" \; \
  split-window -h -p 50 "uvicorn mpes-llm.app:app --reload --host 0.0.0.0 --port 8001" \; \
  split-window -v -p 50 "uvicorn mpes-tts.app:app --reload --host 0.0.0.0 --port 8002" \; \
  split-window -v -p 50 "uvicorn maestro.app:app --reload --host 0.0.0.0 --port 7000" \; \
  attach-session
