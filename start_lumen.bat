@echo off
echo ========================================
echo    Starting Lumen Assessment Platform
echo ========================================
echo.

REM Check if running in project directory
if not exist "manage.py" (
    echo ERROR: manage.py not found. Please run this script from the project root directory.
    pause
    exit /b 1
)

echo [1/3] Starting LM Studio...
echo.

REM Start LM Studio (adjust path if needed)
REM You may need to change this path to where LM Studio is installed
start "C:\Program Files\LM Studio\LM Studio.exe"

REM Wait for LM Studio to initialize
echo Waiting for LM Studio to start (15 seconds)...
timeout /t 15 /nobreak >nul

echo.
echo [2/3] Starting ngrok tunnel...
echo.

REM Start ngrok in a new window
REM Make sure ngrok is in your PATH or provide full path
start "ngrok" cmd /k "ngrok http 8000"

REM Wait for ngrok to establish tunnel
echo Waiting for ngrok to establish tunnel (5 seconds)...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] Starting Django development server...
echo.

REM Start Django server
echo Django server starting at http://127.0.0.1:8000/
echo.
echo ========================================
echo     All services started successfully!
echo ========================================
echo.
echo LM Studio: Running in separate window
echo ngrok: Check ngrok window for public URL
echo Django: http://127.0.0.1:8000/
echo.
echo Press Ctrl+C to stop Django server
echo Close LM Studio and ngrok windows manually when done
echo.

python manage.py runserver

pause
