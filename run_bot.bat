@echo off
chcp 65001 >nul
title Investor Tracker - Telegram Bot

cd /d "%~dp0"

if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo TELEGRAM_BOT_TOKEN 환경변수를 설정하세요.
    echo.
    echo 설정 방법:
    echo   set TELEGRAM_BOT_TOKEN=your_bot_token_here
    echo   run_bot.bat
    echo.
    echo 또는:
    echo   run_bot.bat your_bot_token_here
    echo.
    if "%1"=="" (
        pause
        exit /b 1
    ) else (
        set TELEGRAM_BOT_TOKEN=%1
    )
)

echo Starting Telegram bot...
python -m src.bot.telegram_bot
