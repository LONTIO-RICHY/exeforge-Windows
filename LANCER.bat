@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 main.py & goto :fin)
python main.py
:fin
if errorlevel 1 pause
