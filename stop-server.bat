@echo off
chcp 65001 >nul
echo Stopping Investor Tracker Server...

:: Stop Streamlit
taskkill /f /im streamlit.exe 2>nul
taskkill /f /im python.exe /fi "WINDOWTITLE eq *streamlit*" 2>nul

:: Stop Cloudflare Tunnel
taskkill /f /im cloudflared.exe 2>nul

echo.
echo Server stopped.
pause
