@echo off

echo Checking requirements...

where py >nul 2>&1
if %errorlevel% equ 0 (
    set PY=py -3
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PY=python
    ) else (
        echo [ERROR] Python not found. Install Python 3 and make sure it's in PATH.
        pause
        exit /b 1
    )
)

%PY% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python failed to run.
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in PATH.
    pause
    exit /b 1
)

echo Checking Python packages...
%PY% -m pip install --quiet -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
    echo [WARN] node_modules not found. Running npm install...
    cd /d "%~dp0frontend" && npm install
)

echo Starting backend and frontend...

start "Backend" cmd /k "cd /d %~dp0backend && %PY% main.py"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Both services started in separate windows.
echo   Backend:  http://localhost:5000
echo   Frontend: http://localhost:5173
