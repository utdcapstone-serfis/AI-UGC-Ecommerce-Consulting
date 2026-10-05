@echo off
title Stop Postiz
cd /d "%~dp0"
echo Stopping Postiz...
docker compose down
echo.
echo Postiz stopped. Your data is kept for next time.
timeout /t 3 /nobreak >nul
