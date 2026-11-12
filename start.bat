@echo off
chcp 65001 >nul
cd /d "%~dp0"
python selection_to_ai.py
pause
