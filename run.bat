@echo off
rem Launch the DR Price Evaluator using the bundled virtual environment.
cd /d "%~dp0"
".venv\Scripts\pythonw.exe" main.py
