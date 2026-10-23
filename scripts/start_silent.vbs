' ==============================================================================
' Nanjing LBS Platform - Windows 静默后台启动脚本 (无任何 CMD 黑框)
' ==============================================================================
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
baseDir = fso.GetParentFolderName(scriptDir)
serverScript = baseDir & "\dashboard_server.py"

pythonExe = "python.exe"
If fso.FileExists("C:\ProgramData\anaconda3\pythonw.exe") Then
    pythonExe = "C:\ProgramData\anaconda3\pythonw.exe"
ElseIf fso.FileExists("C:\ProgramData\anaconda3\python.exe") Then
    pythonExe = "C:\ProgramData\anaconda3\python.exe"
Else
    pythonExe = "python.exe"
End If

WshShell.CurrentDirectory = baseDir
WshShell.Run """" & pythonExe & """ """ & serverScript & """", 0, False

Set fso = Nothing
Set WshShell = Nothing
