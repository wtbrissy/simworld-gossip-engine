@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate (
  echo Virtual environment not found. Running install first...
  call install_windows.bat
)
call .venv\Scripts\activate
set SIMWORLD_USE_OLLAMA=1
set OLLAMA_MODEL=qwen2.5:3b
echo Starting SimWorld Gossip Engine v7 English Demo with optional Ollama AI summaries, director notes, dialogues, inner monologues and daily serial stories...
echo Make sure Ollama is already running and the model exists.
python -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
