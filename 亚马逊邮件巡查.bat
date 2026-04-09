@echo off
setlocal enabledelayedexpansion

:: ========================================
:: 1. 管理员权限自动检测与提权
:: ========================================
:check_Permissions
    net session >nul 2>&1
    if %errorLevel% == 0 (
        echo [OK] 已获得管理员权限运行
    ) else (
        echo [ERROR] 正在尝试获取管理员权限...
        powershell -Command "Start-Process '%~f0' -Verb RunAs"
        exit /b
    )

:: 2. 环境编码修复 (解决 CMD 窗口乱码)
chcp 65001 >nul
:: 强制 Python 以 UTF-8 编码写入日志
set PYTHONIOENCODING=utf-8

:: 3. 路径配置 (请确保路径无误)
set "PROJECT_DIR=E:\Pycharm Project\lingxing"
set "LOG_DIR=E:\Documents\Logs"
set "PYTHON_EXE=E:\Pycharm Project\.venv\Scripts\python.exe"

:: 4. 自动创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 5. 定义日志文件名 (按日期命名)
set LOG_FILE="%LOG_DIR%\MailList_%date:~0,4%-%date:~5,2%-%date:~8,2%.log"

:: 6. 开始记录任务
echo ======================================== >> %LOG_FILE%
echo   任务启动时刻: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%

:: --- 环境预处理 ---
:: 切换到项目目录
cd /d "%PROJECT_DIR%"

:: --- 执行 mail_List.py 脚本 ---
echo [%time%] [任务开始] 正在运行 mail_List.py... >> %LOG_FILE%
echo 正在执行邮件巡查任务...

:: 执行命令 (使用引号包裹路径以处理空格)
"%PYTHON_EXE%" "mail_List.py" >> %LOG_FILE% 2>&1

:: 记录结束状态
echo. >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%
echo   任务全部结束: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%

:: 7. 屏幕提示并静默退出
echo 任务执行完毕，日志已更新。
timeout /t 3 >nul
exit