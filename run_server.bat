@echo off
setlocal
cd /d "%~dp0"

echo [Polygon Rush Server]
echo Checking for Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed.
    pause
    exit /b 1
)

IF NOT EXIST "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo Installing requirements...
pip install -r requirements.txt

echo Starting Server...
start cmd /k "cd server & uvicorn main:app --host 127.0.0.1 --port 8004"

echo Starting ngrok...
start cmd /k "ngrok http --url=simplify-bring-armory.ngrok-free.dev 8004"
