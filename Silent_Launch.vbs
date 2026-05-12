Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c Start_AetherControl.bat", 0, false
Set WshShell = Nothing
