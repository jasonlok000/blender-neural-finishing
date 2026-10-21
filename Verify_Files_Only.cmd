@echo off
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m neural_finishing.worker --probe
pause
