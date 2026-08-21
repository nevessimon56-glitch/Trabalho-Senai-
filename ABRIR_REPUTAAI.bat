@echo off
chcp 65001 >nul
title ReputaAI
cd /d "%~dp0"

if exist "ReputaAI.html" (
    start "" "%~dp0ReputaAI.html"
    exit /b 0
)

if exist "reputai.html" (
    start "" "%~dp0reputai.html"
    exit /b 0
)

echo Arquivo ReputaAI.html nao encontrado nesta pasta.
echo Baixe o projeto completo do GitHub e execute este .bat de novo.
pause
