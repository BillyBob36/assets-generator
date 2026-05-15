@echo off
REM Assets Generator — start the local web app
cd /d "%~dp0"
echo Demarrage du serveur Assets Generator...
echo Ouvre http://localhost:8000 dans ton navigateur.
echo Ctrl+C pour arreter.
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
