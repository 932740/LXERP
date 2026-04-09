@echo off
setlocal enabledelayedexpansion
:: 设置代码页为 UTF-8 以支持中文显示
chcp 65001 >nul

:: 1. 定位最新修改的 Excel 文件
set "LATEST_FILE="
for /f "delims=" %%i in ('dir "*.xlsx" /b /o-d /a-d 2^>nul') do (
    set "LATEST_FILE=%%i"
    goto :run_git
)

:run_git
if "%LATEST_FILE%"=="" (
    echo [Error] No .xlsx file found in the current directory.
    pause
    exit
)

echo [Info] Target file found: %LATEST_FILE%

:: 2. 执行 Git 操作
:: 切换至 main 分支并同步远程状态
git checkout main >nul 2>&1
git fetch origin main >nul 2>&1

:: 重置暂存区，确保仅添加目标文件
git reset >nul 2>&1
git add "%LATEST_FILE%"

:: 提交并推送到远程仓库
git commit -m "Auto Update %LATEST_FILE%"
git push origin main

echo [Info] Git operations completed.
timeout /t 3
exit
