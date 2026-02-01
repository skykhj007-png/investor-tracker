@echo off
chcp 65001 >nul
title Investor Tracker

cd /d "%~dp0"

if "%1"=="" (
    python -m src.main menu
) else (
    python -m src.main %*
)
