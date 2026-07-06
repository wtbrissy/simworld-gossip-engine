@echo off
cd /d "%~dp0"
echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate
echo Installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Install complete. Run run_windows.bat to start SimWorld Gossip Engine v7 English Demo.
pause
