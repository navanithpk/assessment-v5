@echo off
echo ================================================================
echo AI Tagging System - Installation Script
echo ================================================================
echo.

echo [1/3] Installing Python dependencies...
pip install pytesseract pillow requests

echo.
echo [2/3] Checking Tesseract OCR installation...
where tesseract >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Tesseract OCR is installed
    tesseract --version
) else (
    echo [WARNING] Tesseract OCR not found in PATH
    echo.
    echo Please install Tesseract OCR manually:
    echo   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo   2. Install to: C:\Program Files\Tesseract-OCR
    echo   3. Add to system PATH
    echo.
)

echo.
echo [3/3] Testing LMStudio connection...
python test_lmstudio_prompt.py

echo.
echo ================================================================
echo Installation complete!
echo ================================================================
echo.
echo Next steps:
echo   1. Ensure LMStudio is running (http://localhost:1234)
echo   2. Run: python test_lmstudio_prompt.py
echo   3. Access AI Tagging from Teacher Dashboard
echo   4. View logs at: /teacher/ai-logs/
echo.
echo For detailed setup instructions, see: AI_TAGGING_README.md
echo.
pause
