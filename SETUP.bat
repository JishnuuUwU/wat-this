@echo off
setlocal
cd /d "%~dp0"

:: 1. Check local installed Python 3.12
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist "%PY_EXE%" goto :launch

set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY_EXE%" goto :launch

:: 2. Check system PATH pythonw
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=pythonw"
    goto :launch
)

:: 3. Check system PATH python
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :launch
)

:: 4. Auto-install Python via winget if completely missing
echo [INFO] Python is not installed. Installing Python 3.12 automatically...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"

:launch
start "" "%PY_EXE%" "%~dp0src\setup.py"
exit /b 0
