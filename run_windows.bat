@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate (
  echo Virtual environment not found. Running install first...
  call install_windows.bat
)
call .venv\Scripts\activate
echo Starting SimWorld Gossip Engine v7 English Demo...
echo Open on this PC: http://127.0.0.1:8000
echo For phone access, use your PC IPv4 address, for example: http://192.168.1.10:8000
echo Keep this window open.
python -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
