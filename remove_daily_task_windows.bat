@echo off
echo Removing Windows Scheduled Task: M6_SimWorld_AutoStory_2355
schtasks /Delete /TN "M6_SimWorld_AutoStory_2355" /F
echo Done.
pause
