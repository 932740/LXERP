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
        echo [提示] 权限不足，正在尝试以管理员身份重启...
        powershell -Command "Start-Process '%~f0' -Verb RunAs"
        exit /b
    )

:: 2. 环境编码修复 (解决 CMD 窗口乱码)
chcp 65001 >nul
:: 强制 Python 以 UTF-8 编码写入日志
set PYTHONIOENCODING=utf-8

:: 3. 路径配置
:: 保持了你在变量定义时使用引号，但在调用时也加引号的防御性写法
set "PROJECT_DIR=C:\Path\To\Your\Project"
set "LOG_DIR=C:\Path\To\Your\Logs"
set "PYTHON_EXE=C:\Path\To\Your\venv\Scripts\python.exe"

:: 4. 自动创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 5. 定义日志文件名 (按日期命名)
set LOG_FILE="%LOG_DIR%\Amazon_Task_%date:~0,4%-%date:~5,2%-%date:~8,2%.log"

:: 6. 开始记录任务
echo ======================================== >> %LOG_FILE%
echo    Task Started: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%

:: 切换到项目工作目录
cd /d "%PROJECT_DIR%"

:: --- 执行第一个脚本：查询数据 ---
echo [%time%] Running asinDaily_list.py... >> %LOG_FILE%
echo 正在执行 asinDaily_list.py...
"%PYTHON_EXE%" "asinDaily_list.py" >> %LOG_FILE% 2>&1

echo. >> %LOG_FILE%

echo ======================================== >> %LOG_FILE%
echo    Task Completed: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%

:: 7. 屏幕提示并退出
echo 所有程序执行完毕，正在关闭窗口...
:: 留出 3 秒显示时间
timeout /t 3 >nul 
exit
