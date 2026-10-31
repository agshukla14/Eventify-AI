@echo off
setlocal enabledelayedexpansion

:: Switch to the directory containing this batch script
cd /d "%~dp0"

:: Set console codepage to UTF-8 and set Python encoding
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ======================================================================
echo    Celebration ^& Event Planner - Windows Startup
echo ======================================================================
echo.

:: 1. Check for .env file; create from .env.example if missing (never overwrite)
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example template...
        copy ".env.example" ".env" >nul
        echo [INFO] .env created. You can optionally add your GEMINI_API_KEY there.
    )
)

:: 2. Find Python executable
set "PYTHON_EXE="

:: Check virtual environment python first
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [OK] Using virtual environment: %PYTHON_EXE%
) else (
    :: Check system python
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
        echo [OK] Using system Python from PATH
    ) else (
        where py >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=py"
            echo [OK] Using Python Launcher (py)
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo.
    echo [ERROR] Python 3.11+ was not found on your system!
    echo Please install Python 3.11 or higher from https://python.org
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: 3. Check or create virtual environment if not present
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment (.venv) not found. Creating virtual environment...
    %PYTHON_EXE% -m venv .venv
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON_EXE=.venv\Scripts\python.exe"
        echo [OK] Virtual environment created successfully.
    ) else (
        echo [WARN] Could not create .venv; proceeding with %PYTHON_EXE%
    )
)

:: 4. Verify / install Python backend dependencies
echo [INFO] Checking Python dependencies...
%PYTHON_EXE% -c "import fastapi, uvicorn, pydantic, sqlalchemy, reportlab" >nul 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Installing backend dependencies from backend\requirements.txt...
    if exist ".venv\Scripts\pip.exe" (
        .venv\Scripts\pip.exe install -r backend\requirements.txt
    ) else (
        %PYTHON_EXE% -m pip install -r backend\requirements.txt
    )
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Python dependencies. Please check network connection.
        pause
        exit /b 1
    )
    echo [OK] Python dependencies installed.
) else (
    echo [OK] Python dependencies are verified.
)

:: 5. Check frontend production build (frontend\dist\index.html)
if not exist "frontend\dist\index.html" (
    echo [INFO] Frontend build (frontend\dist) not found.
    echo [INFO] Checking for Node.js and npm...
    where npm >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARN] Node.js / npm is not installed or not in PATH!
        echo [WARN] The backend will run, but the UI cannot be built automatically.
        echo [WARN] Please install Node.js (v18+) from https://nodejs.org
    ) else (
        echo [INFO] Building frontend assets (this only happens once)...
        cd frontend
        if not exist "node_modules" (
            echo [INFO] Running npm install...
            call npm install
        )
        echo [INFO] Running npm run build...
        call npm run build
        cd ..
        if exist "frontend\dist\index.html" (
            echo [OK] Frontend built successfully!
        ) else (
            echo [WARN] Frontend build did not complete as expected.
        )
    )
) else (
    echo [OK] Frontend production build verified.
)

:: 6. Launch Application
echo.
echo ======================================================================
echo  Application is starting!
echo.
echo  Website Address:       http://localhost:8000
echo  API Health Check:      http://localhost:8000/api/health
echo  Interactive API Docs:  http://localhost:8000/docs
echo ======================================================================
echo.

%PYTHON_EXE% start_app.py
if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Application terminated with an error.
    pause
)
