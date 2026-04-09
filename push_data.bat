@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

:: 1. 定位最新的 Excel
set "LATEST_FILE="
for /f "delims=" %%i in ('dir "*.xlsx" /b /o-d /a-d 2^>nul') do (
    set "LATEST_FILE=%%i"
    goto :run_git
)

:run_git
if "%LATEST_FILE%"=="" (
    echo [Error] No file found.
    exit
)

echo Target: %LATEST_FILE%

:: 2. 执行 Git 操作
:: 确保我们在 main 分支
git checkout main >nul 2>&1
git fetch origin main
git reset
git add "%LATEST_FILE%"
git commit -m "Auto Update %LATEST_FILE%"
git push origin main

echo Done!
timeout /t 3
exit
