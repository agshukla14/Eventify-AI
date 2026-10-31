# PowerShell startup script for Celebration & Event Planner
Set-Location -Path $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Celebration & Event Planner - Windows Startup (PowerShell)" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check for .env file
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Write-Host "[INFO] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 2. Find Python executable
$pythonExe = ""
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonExe = ".\.venv\Scripts\python.exe"
    Write-Host "[OK] Using virtual environment: $pythonExe" -ForegroundColor Green
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
    Write-Host "[OK] Using system Python from PATH" -ForegroundColor Green
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonExe = "py"
    Write-Host "[OK] Using Python Launcher (py)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Python 3.11+ was not found on your system!" -ForegroundColor Red
    Write-Host "Please install Python from https://python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 3. Create .venv if not present
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[INFO] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    & $pythonExe -m venv .venv
    if (Test-Path ".\.venv\Scripts\python.exe") {
        $pythonExe = ".\.venv\Scripts\python.exe"
        Write-Host "[OK] Virtual environment created successfully." -ForegroundColor Green
    }
}

# 4. Check dependencies
Write-Host "[INFO] Verifying backend dependencies..." -ForegroundColor Gray


= & $pythonExe -c "import fastapi, uvicorn, pydantic, sqlalchemy, reportlab" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing Python dependencies..." -ForegroundColor Yellow
    & $pythonExe -m pip install -r backend\requirements.txt
} else {
    Write-Host "[OK] Python dependencies verified." -ForegroundColor Green
}

# 5. Check frontend build
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "[INFO] Building frontend production bundle..." -ForegroundColor Yellow
    Push-Location frontend
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build
    Pop-Location
} else {
    Write-Host "[OK] Frontend production build verified." -ForegroundColor Green
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Website Address:       http://localhost:8000" -ForegroundColor Green
Write-Host " API Health Check:      http://localhost:8000/api/health" -ForegroundColor Gray
Write-Host " Interactive API Docs:  http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

& $pythonExe start_app.py
