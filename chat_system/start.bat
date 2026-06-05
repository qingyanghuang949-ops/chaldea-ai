@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   CHALDEA AI Communication Terminal
echo   人理継続保障機関 カルデア
echo ============================================
echo.
echo Starting server...
echo Open http://localhost:5000 in your browser
echo.
python app.py
pause
