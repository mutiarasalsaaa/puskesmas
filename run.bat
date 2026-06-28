@echo off
echo ============================================
echo   Sistem Rawat Jalan Puskesmas
echo ============================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan!
    echo Silakan install Python dari https://python.org
    pause
    exit
)
pip install Flask --quiet
echo Menjalankan aplikasi...
echo Buka browser: http://localhost:5000
echo Tekan CTRL+C untuk berhenti
echo.
python app.py
pause
