@echo off
cd /d "%~dp0"
echo Starting AetherControl IoT Hub...
start /min "" python app.py
timeout /t 3 /nobreak > nul
start http://127.0.0.1:5000
echo.
echo ==========================================
echo AetherControl is now running in the background!
echo You can close this window.
echo ==========================================
pause
