@echo off
chcp 65001 >nul
echo ================================================================
echo   南京同城活动 LBS 平台 - 运行状态检测
echo ================================================================

python -c "import urllib.request, json; res = json.loads(urllib.request.urlopen('http://127.0.0.1:8765/api/health').read().decode()); print('[✓] 服务运行正常 (版本: ' + res['version'] + ', 活动总数: ' + str(res['cache']['count']) + ' 条)'); print('    局域网访问地址:'); [print('    - http://' + ip + ':8765') for ip in res['lan_ips']]" 2>nul

if %errorlevel% neq 0 (
    echo [!] 服务未运行或端口 8765 无法连接。
    echo 您可以双击 %~dp0start_silent.vbs 启动后台服务。
)
pause
