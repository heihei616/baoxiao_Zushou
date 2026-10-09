@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal

set "BASE=%~dp0"
cd /d "%BASE%"

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where py >nul 2>nul && set "PY=py"
)
if not defined PY (
    echo Python not found. Please install Python 3 and check "Add to PATH".
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ========================================
echo   QingHe Reimbursement Assistant (demo)
echo   Put invoices (.xml / .pdf) into data\inbox\ then run.
echo ========================================
echo.

"%PY%" demo.py
set "RC=%errorlevel%"

echo.
if %RC%==0 (
    echo Done. Reimbursement packet and ledger are in data\output\
    echo Open the HTML form in data\output\ with a browser, Ctrl/Cmd+P to save PDF.
    echo Open the CSV ledger in data\output\ with Excel.
) else (
    echo Failed (exit code %RC%). Check data\inbox\ invoices.
)
echo.
echo Press any key to close...
pause >nul
