@echo off
cd /d %~dp0
if not exist .venv (
  echo Please run install_windows.bat first.
  pause
  exit /b 1
)
echo Creating Windows Scheduled Task: M6_SimWorld_AutoStory_2355
schtasks /Create /TN "M6_SimWorld_AutoStory_2355" /TR "\"%cd%\.venv\Scripts\python.exe\" \"%cd%\daily_task.py\"" /SC DAILY /ST 23:55 /F
echo.
echo Done. When this PC is awake at 23:55, SimWorld will advance one day and write a daily story.
echo Stories are saved in exports\serial.
pause
