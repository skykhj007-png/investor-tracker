@echo off
chcp 65001 >nul
title Investor Tracker - Web Dashboard

cd /d "%~dp0"
echo Starting web dashboard...
echo.
echo Open browser: http://localhost:8501
echo.
streamlit run src/web/dashboard.py
