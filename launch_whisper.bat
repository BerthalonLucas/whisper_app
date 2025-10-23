@echo off
title Voxtral - Voice Transcription App
echo.
echo ========================================
echo   VOXTRAL - Voice Transcription App
echo ========================================
echo.
echo Demarrage de l'application...
echo.

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Lancer l'application Python
python app.py

REM Desactiver l'environnement virtuel a la fin
deactivate

pause
