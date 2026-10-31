@echo off
setlocal enabledelayedexpansion

:: 1. Determine project root and switch to it safely
cd /d "%~dp0"

echo =====================================================================
echo  SUPPLIER ACKNOWLEDGEMENT AND SCHEDULE IMPACT MANAGER
echo  One-Command Local Development Environment Startup
echo =====================================================================
echo [INFO] Working directory: %cd%
echo.

:: 2. Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v detected.

:: 3. Check Node.js and npm installation
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not found in system PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not installed or not found in system PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo [OK] Node.js %%v detected.
for /f "tokens=*" %%v in ('npm --version') do echo [OK] npm v%%v detected.

:: 4. Verify required project directories and files exist
if not exist "backend\main.py" (
    echo [ERROR] Required file 'backend\main.py' is missing.
    pause
    exit /b 1
)
if not exist "frontend\package.json" (
    echo [ERROR] Required file 'frontend\package.json' is missing.
    pause
    exit /b 1
)
if not exist "database\schema.sql" (
    echo [ERROR] Required file 'database\schema.sql' is missing.
    pause
    exit /b 1
)
echo [OK] Project files and directory structure verified.

:: 5. Create Python virtual environment if it does not exist
if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating Python virtual environment in .\venv ...
    python -m venv venv --system-site-packages
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)
call venv\Scripts\activate.bat

:: 6. Install backend dependencies only when necessary
if not exist "venv\.deps_installed" (
    echo [SETUP] Installing backend dependencies from requirements.txt ...
    pip install -r backend\requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Backend dependency installation failed.
        pause
        exit /b 1
    )
    echo deps_installed > venv\.deps_installed
    echo [OK] Backend dependencies installed successfully.
) else (
    echo [OK] Backend dependencies already satisfied.
)

:: 7. Install frontend dependencies only when necessary
if not exist "frontend\node_modules" (
    echo [SETUP] Installing frontend dependencies ...
    npm --prefix frontend install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Frontend dependency installation failed.
        pause
        exit /b 1
    )
    echo [OK] Frontend dependencies installed successfully.
) else (
    echo [OK] Frontend dependencies already installed.
)

:: 8. Ensure configuration files (.env) exist
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo [SETUP] Creating backend\.env from template...
        copy backend\.env.example backend\.env >nul
    )
)
if not exist ".env" (
    if exist "backend\.env" (
        copy backend\.env .env >nul
    )
)

:: 9. Check MySQL database connectivity
echo [CHECK] Verifying MySQL database connectivity...
python -m backend.check_db
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] MySQL database connection check failed.
    echo Please make sure your MySQL 8.0 server is running on localhost:3306
    echo and valid credentials are configured in .env.
    echo Application cannot start without persistent database connectivity.
    pause
    exit /b 1
)
echo [OK] MySQL database connection verified.

:: 10. Check if ports 8000 or 5173 are currently occupied
for /f "tokens=5" %%p in ('netstat -aon ^| findstr /r /c:":8000 *.*LISTENING"') do (
    echo [WARN] Port 8000 is already in use by PID %%p. Stopping stale instance...
    taskkill /f /pid %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr /r /c:":5173 *.*LISTENING"') do (
    echo [WARN] Port 5173 is already in use by PID %%p. Stopping stale instance...
    taskkill /f /pid %%p >nul 2>&1
)

:: 11. Display application URLs and shutdown instructions
echo.
echo =====================================================================
echo  LOCAL APPLICATION ADDRESSES:
echo  Frontend Web App:          http://localhost:5173
echo  Backend REST API:          http://localhost:8000
echo  Interactive API Docs:      http://localhost:8000/docs
echo =====================================================================
echo  STOPPING THE APPLICATION:
echo  - Press Ctrl+C in this window and close the backend console window.
echo  - Or run '.\stop.bat' in any terminal window.
echo =====================================================================
echo.
echo Starting FastAPI backend in a dedicated console window...

:: 12. Start FastAPI backend in a separate console window
start "FastAPI Backend - Port 8000" cmd /k "cd /d ""%cd%"" && call venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

:: 13. Start React/Vite development server in this console
echo Starting React Vite frontend server on port 5173...
cd frontend
npm run dev
