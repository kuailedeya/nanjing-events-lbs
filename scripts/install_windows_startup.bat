@echo off
chcp 65001 >nul
echo ================================================================
echo   南京同城活动 LBS 平台 - 安装 Windows 开机自启服务
echo ================================================================

set "TARGET_VBS=%~dp0start_silent.vbs"
set "REPO_ROOT=%~dp0.."
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NanjingLBS.lnk"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%TARGET_VBS%\"'; $s.WorkingDirectory = '%REPO_ROOT%'; $s.Description = 'Nanjing Events LBS Platform AutoStart'; $s.Save()"

if %errorlevel% equ 0 (
    echo [✓] 成功创建开机自启快捷方式！
    echo 目标路径: %SHORTCUT_PATH%
    echo 以后每次开机登录，系统将在后台自动静默启动 LBS 服务 (端口 8765)。
) else (
    echo [!] 创建快捷方式失败，请以管理员权限运行。
)
pause
