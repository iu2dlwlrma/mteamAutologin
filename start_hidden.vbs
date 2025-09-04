CreateObject("WScript.Shell").Run """" & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\start.bat""", 0, True
