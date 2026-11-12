@echo off
chcp 65001 >nul
setlocal
echo 正在启动划词直达豆包工作工具...
echo 按 Ctrl+Q 发送选区；按 Ctrl+Shift+Q 退出脚本。
echo.
set "SCRIPT=%~dp0划词直达豆包.py"
where py >nul 2>nul
if errorlevel 1 goto try_python
py -3.12 "%SCRIPT%"
if errorlevel 1 goto fail
goto done
:try_python
python "%SCRIPT%"
if errorlevel 1 goto fail
goto done
:fail
echo.
echo [启动失败] 请检查 Python 3.12 和依赖安装情况。
echo 使用 py 时安装依赖：py -3.12 -m pip install -r "%~dp0requirements.txt"
echo 使用 python 时安装依赖：python -m pip install -r "%~dp0requirements.txt"
:done
pause
