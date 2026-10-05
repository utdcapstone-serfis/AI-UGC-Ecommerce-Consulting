@echo off
title Postiz
cd /d "%~dp0"

docker info >nul 2>&1
if not errorlevel 1 goto dockerok
echo Docker Desktop is not running. Starting it...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
:waitdocker
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto waitdocker

:dockerok
echo Starting Postiz containers...
docker compose up -d
if errorlevel 1 (
    echo.
    echo Something went wrong starting the containers. See the error above.
    pause
    exit /b 1
)

echo.
echo Waiting for Postiz to come up (first start can take a couple of minutes)...
:waitready
timeout /t 5 /nobreak >nul
curl -s -o nul -f http://localhost:4007/ >nul 2>&1
if errorlevel 1 goto waitready

echo Postiz is ready. Opening your browser...
start "" http://localhost:4007

echo.
echo Container status:
docker compose ps
echo.
echo Postiz is running at http://localhost:4007
echo You can close this window - the containers keep running.
echo.
pause
