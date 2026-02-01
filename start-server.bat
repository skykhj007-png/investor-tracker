@echo off
chcp 65001 >nul
title Investor Tracker Server

echo ========================================
echo   Investor Tracker Server
echo   https://investor.pointing.co.kr
echo ========================================
echo.

cd /d C:\Users\k\investor-tracker

:: Start Cloudflare Tunnel in background
echo [1/2] Starting Cloudflare Tunnel...
start /b "" "C:\Users\k\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" tunnel run investor-tracker

:: Wait a moment for tunnel to connect
timeout /t 3 /nobreak >nul

:: Start Streamlit
echo [2/2] Starting Streamlit Dashboard...
echo.
echo Server running at: https://investor.pointing.co.kr
echo Local: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

python -m streamlit run src/web/dashboard.py --server.port 8501 --server.headless true
