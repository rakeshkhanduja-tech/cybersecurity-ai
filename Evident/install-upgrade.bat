@echo off
setlocal
echo ============================================================
echo Evident: Environment Setup and Dependency Update
echo ============================================================
echo.

if not exist .venv (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment. Ensure Python is installed.
        pause
        exit /b %ERRORLEVEL%
    )
    
    echo [INFO] Installing dependencies into .venv...
    call .venv\Scripts\activate.bat
    
    @rem Safeguard: Prevent loading potentially broken libs from User Roaming AppData
    set PYTHONNOUSERSITE=1
    
    echo [INFO] Updating pip...
    python -m pip install --upgrade pip
    
    echo [INFO] Installing packages from requirements.txt...
    echo [NOTE] This step may take 5-15 minutes if large libraries like 'torch' or 'sentence-transformers' are being downloaded.
    python -m pip install -v -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b %ERRORLEVEL%
    )
    echo [OK] Environment setup complete.
) else (
    echo [OK] Virtual environment found. Activating...
    call .venv\Scripts\activate.bat
    
    @rem Safeguard: Prevent loading potentially broken libs from User Roaming AppData
    set PYTHONNOUSERSITE=1
    
    echo [INFO] Checking for dependency updates...
    echo [NOTE] This may take a moment. If 'torch' or 'sentence-transformers' need updating, it could take several minutes.
    python -m pip install --upgrade pip
    python -m pip install -v -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Dependency update failed.
        pause
        exit /b %ERRORLEVEL%
    )
    echo [OK] Dependencies are up to date.
)

echo.
echo Setup complete. You can now run start.bat
timeout /t 3
