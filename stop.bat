@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo =====================================================================
echo  SUPPLIER ACKNOWLEDGEMENT AND SCHEDULE IMPACT MANAGER
echo  Stopping Local Development Services (Ports 8000 and 5173)...
echo =====================================================================
echo.

set STOPPED=0

:: Terminate process listening on Port 8000 (Backend API / Uvicorn)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr /r /c:":8000 *.*LISTENING"') do (
    echo [STOP] Terminating Backend process (PID %%p) on Port 8000...
    taskkill /f /pid %%p >nul 2>&1
    set STOPPED=1
)

:: Terminate process listening on Port 5173 (Frontend / Vite)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr /r /c:":5173 *.*LISTENING"') do (
    echo [STOP] Terminating Frontend process (PID %%p) on Port 5173...
    taskkill /f /pid %%p >nul 2>&1
    set STOPPED=1
)

if "%STOPPED%"=="0" (
    echo [INFO] No active servers found running on port 8000 or 5173.
) else (
    echo [OK] All Supplier Schedule Manager development servers have been stopped.
)

echo.
echo =====================================================================

