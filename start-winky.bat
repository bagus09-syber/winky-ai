@echo off
title Winky AI

echo ==========================================
echo            WINKY AI STARTUP
echo ==========================================
echo.

echo [1/3] Mengecek Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1

if errorlevel 1 (
    echo Ollama belum berjalan.
    echo Menyalakan Ollama...
    start "Ollama" cmd /k "ollama serve"
    timeout /t 3 /nobreak >nul
) else (
    echo Ollama sudah berjalan.
)

echo.
echo [2/3] Menyalakan Backend...
start "Winky Backend" cmd /k "cd /d D:\winky\backend && python -m uvicorn main:app --host 127.0.0.1 --port 8001"

timeout /t 2 /nobreak >nul

echo.
echo [3/3] Menyalakan Frontend...
start "Winky Frontend" cmd /k "cd /d D:\winky\frontend && npm run dev"

echo.
echo ==========================================
echo WINKY AI SEDANG DIMULAI
echo ==========================================
echo.
echo Backend:
echo http://127.0.0.1:8001
echo.
echo Frontend biasanya:
echo http://localhost:5173
echo atau http://localhost:5174
echo.
pause