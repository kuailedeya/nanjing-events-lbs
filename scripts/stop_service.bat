@echo off
chcp 65001 >nul
echo ================================================================
echo   南京同城活动 LBS 平台 - 停止后台服务
echo ================================================================

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo [*] 正在终止端口 8765 对应的服务进程 (PID: %%a)...
    taskkill /F /PID %%a
)

echo [✓] 操作完成。
pause
