@echo off
python tools\serve.py %*
if errorlevel 1 (
    echo.
    echo If 'python' was not found, check that Python 3.12+ is in your PATH.
    pause
)
