#!/bin/zsh
set -e

cd "/Users/lawrencecheng/Documents/New project"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
