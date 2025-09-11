#!/bin/bash

# Run each model on a separate tmux window
tmux new-session "python maestro/app.py" \; \
  split-window -h -p 50 "python mpes-llm/app.py" \; \
  split-window -v -p 50 "python mpes-tts/app.py" \; \
  split-window -v -p 50 "python mpes-stt/app.py" \; \
  attach-session
