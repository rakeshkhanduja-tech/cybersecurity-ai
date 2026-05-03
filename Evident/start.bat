@echo off
setlocal
echo ============================================================
echo Starting Evident Security Intelligence Agent
echo ============================================================
echo.

if not exist ".venv" (
    echo [ERROR] Virtual environment .venv not found.
    echo [INFO] Please run install-upgrade.bat first to set up the environment.
    pause
    exit /b 1
)

echo [OK] Virtual environment found. Activating...
call .venv\Scripts\activate.bat

@rem Safeguard: Prevent loading potentially broken libs from User Roaming AppData
set PYTHONNOUSERSITE=1
echo.
echo Starting web server with mock LLM...
echo.
python main.py --mode web --mock-llm

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Application failed to start.
    pause
)
