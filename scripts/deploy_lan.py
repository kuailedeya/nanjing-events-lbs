# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from pathlib import Path

def setup_startup():
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        print("[!] 无法获取 APPDATA 环境变量")
        return False
    startup_dir = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
    shortcut_path = startup_dir / "NanjingLBS.lnk"
    vbs_path = Path(r"E:\usage\scripts\start_silent.vbs")

    ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{str(shortcut_path)}')
$s.TargetPath = 'wscript.exe'
$s.Arguments = '"{str(vbs_path)}"'
$s.WorkingDirectory = 'E:\\usage'
$s.Description = 'Nanjing Events LBS Platform AutoStart'
$s.Save()
'''
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
        if shortcut_path.exists():
            print(f"[✓] 开机自启快捷方式创建成功: {shortcut_path}")
            return True
        else:
            print(f"[!] 快捷方式创建失败: {res.stderr}")
            return False
    except Exception as e:
        print(f"[!] 创建失败: {e}")
        return False

def check_firewall():
    ps_cmd = 'New-NetFirewallRule -DisplayName "Nanjing Events LBS" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow -ErrorAction Stop'
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
        if res.returncode == 0:
            print("[✓] Windows 防火墙已开放入站端口 8765 (局域网畅通)")
        else:
            if "already exists" in res.stderr or "已存在" in res.stderr:
                print("[✓] Windows 防火墙规则已存在 (端口 8765 已放行)")
            else:
                print("[i] 提示: 若局域网其他设备无法连接，请右键以管理员运行添加防火墙入站规则 8765。")
    except Exception:
        pass

def get_lan_ips():
    import socket
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    return ips

if __name__ == "__main__":
    print("=" * 60)
    print("  南京同城活动 LBS 平台 - Windows 本地/局域网常驻自启部署")
    print("=" * 60)
    setup_startup()
    check_firewall()
    lan_ips = get_lan_ips()
    print("\n[✓] 部署配置完成！可在手机/电脑浏览器中直接访问：")
    print("    - 本机访问:  http://127.0.0.1:8765")
    for ip in lan_ips:
        print(f"    - 局域网访问: http://{ip}:8765")
    print("\n[i] 管理指引:")
    print("    - 开机自启: 已自动生效（开机即在后台静默运行）")
    print("    - 查看状态: 双击 E:\\usage\\scripts\\status.bat")
    print("    - 停止服务: 双击 E:\\usage\\scripts\\stop_service.bat")
    print("    - 手动启动: 双击 E:\\usage\\scripts\\start_silent.vbs")
