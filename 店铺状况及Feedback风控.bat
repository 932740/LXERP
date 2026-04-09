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
        echo [INFO] 正在尝试获取管理员权限...
        powershell -Command "Start-Process '%~f0' -Verb RunAs"
        exit /b
    )

:: 2. 环境编码修复 (解决 CMD 窗口乱码)
chcp 65001 >nul
:: 强制 Python 以 UTF-8 编码处理输入输出
set PYTHONIOENCODING=utf-8

:: 3. 路径配置 (请根据实际环境修改占位路径)
set "PROJECT_DIR=C:\Path\To\Your\Project"
set "LOG_DIR=C:\Path\To\Your\Logs"
set "PYTHON_EXE=C:\Path\To\Your\venv\Scripts\python.exe"

:: 4. 自动创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 5. 定义日志文件名 (按日期命名)
set LOG_FILE="%LOG_DIR%\Task_%date:~0,4%-%date:~5,2%-%date:~8,2%.log"

:: 6. 开始记录任务
echo ======================================== >> %LOG_FILE%
echo    Task Started: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%

:: 切换到项目目录
cd /d "%PROJECT_DIR%"

:: --- 执行第一个脚本 (dianpu) ---
echo [%time%] [Step 1/3] Running get_dianpu.py... >> %LOG_FILE%
echo 正在执行 get_dianpu.py...
"%PYTHON_EXE%" "get_dianpu.py" >> %LOG_FILE% 2>&1
echo. >> %LOG_FILE%

:: --- 执行第二个脚本 (Feedback) ---
echo [%time%] [Step 2/3] Running get_Feedback.py... >> %LOG_FILE%
echo 正在执行 get_Feedback.py...
"%PYTHON_EXE%" "get_Feedback.py" >> %LOG_FILE% 2>&1
echo. >> %LOG_FILE%

:: --- 执行第三个脚本 (Review) ---
echo [%time%] [Step 3/3] Running get_Review.py... >> %LOG_FILE%
echo 正在执行 get_Review.py...
"%PYTHON_EXE%" "get_Review.py" >> %LOG_FILE% 2>&1
echo. >> %LOG_FILE%

echo ======================================== >> %LOG_FILE%
echo    All Tasks Finished: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%

:: 7. 屏幕提示并退出
echo.
echo ========================================
echo    所有程序执行完毕！
echo    (包含: dianpu, Feedback, Review)
echo    窗口将在 3 秒后自动关闭...
echo ========================================
timeout /t 3 >nul
exit
