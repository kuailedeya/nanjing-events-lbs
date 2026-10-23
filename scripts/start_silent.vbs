' ==============================================================================
' Nanjing LBS Platform - Windows 静默后台启动脚本 (无任何 CMD 黑框)
' ==============================================================================
Set WshShell = CreateObject("WScript.Shell")
strPath = "C:\ProgramData\anaconda3\python.exe E:\usage\dashboard_server.py"
WshShell.Run strPath, 0, False
Set WshShell = Nothing
