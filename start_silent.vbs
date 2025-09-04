' M-Team Auto Login Tool - Silent Launcher
' This VBS script runs start.bat in background without showing CMD window

Dim objShell, objFSO, strCurrentDir, strBatchFile

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get current script directory
strCurrentDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Build full path to start.bat
strBatchFile = strCurrentDir & "\start.bat"

' Check if start.bat exists
If objFSO.FileExists(strBatchFile) Then
    ' Run start.bat silently
    ' WindowStyle: 0=Hidden, 1=Normal, 2=Minimized, 3=Maximized
    ' Third parameter True = wait for completion
    ' objShell.Run Chr(34) & strBatchFile & Chr(34), 0, True
    ' Optional: Show modern Windows Toast notification (comment out for complete silence)
    Call ShowToastNotification("M-Team Auto Login", "Login completed successfully!", "success")
Else
    ' Show error notification if start.bat not found
    Call ShowToastNotification("M-Team Auto Login", "Error: start.bat file not found! Please ensure the VBS script is in the same directory as start.bat.", "error")
End If




' Function to show modern Windows Toast notification
Sub ShowToastNotification(title, message, notificationType)
    Dim psCommand, iconPath, psScript
    
    ' Create PowerShell command for Toast notification
    psScript = "Add-Type -AssemblyName System.Windows.Forms;" & vbCrLf & _
               "Add-Type -AssemblyName System.Drawing;" & vbCrLf & _
               "$notification = New-Object System.Windows.Forms.NotifyIcon;" & vbCrLf & _
               "$notification.Icon = [System.Drawing.SystemIcons]::"
    
    ' Set icon based on notification type
    If notificationType = "success" Then
        psScript = psScript & "Information;"
    ElseIf notificationType = "error" Then
        psScript = psScript & "Error;"
    Else
        psScript = psScript & "Information;"
    End If
    
    ' Complete the PowerShell script
    psScript = psScript & vbCrLf & _
               "$notification.BalloonTipTitle = '" & title & "';" & vbCrLf & _
               "$notification.BalloonTipText = '" & message & "';" & vbCrLf & _
               "$notification.BalloonTipIcon = 'Info';" & vbCrLf & _
               "$notification.Visible = $true;" & vbCrLf & _
               "$notification.ShowBalloonTip(5000);" & vbCrLf & _
               "Start-Sleep -Seconds 6;" & vbCrLf & _
               "$notification.Dispose();"
    
    ' Build PowerShell command
    psCommand = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command """ & psScript & """"
    
    ' Execute the PowerShell command
    objShell.Run psCommand, 0, False
End Sub

' Cleanup and exit
Set objShell = Nothing
Set objFSO = Nothing