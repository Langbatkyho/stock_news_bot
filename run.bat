@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

:: Kiểm tra kích hoạt môi trường ảo theo thứ tự ưu tiên
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist ..\.venv\Scripts\activate.bat (
    call ..\.venv\Scripts\activate.bat
) else if exist "%USERPROFILE%\.venv\Scripts\activate.bat" (
    call "%USERPROFILE%\.venv\Scripts\activate.bat"
)

python main.py

if "%~1" neq "nopause" (
    pause
)
