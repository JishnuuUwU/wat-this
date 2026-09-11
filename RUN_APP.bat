@echo off
setlocal
cd /d "%~dp0"

:: Check local installed Python 3.12 pythonw.exe
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist "%PY_EXE%" goto :launch

set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY_EXE%" goto :launch

where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=pythonw"
    goto :launch
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :launch
)

echo [ERROR] Python not found. Please run SETUP.bat first to configure the environment.
pause
exit /b 1

:launch
start "" "%PY_EXE%" "%~dp0src\wat_this.py"
exit /b 0
