$trigger = New-ScheduledTaskTrigger -Daily -At "15:00" #在下午三点自动备份
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File D:\Code\python\KGRS\backup.ps1"
$settings = New-ScheduledTaskSettingsSet -WakeToRun
Register-ScheduledTask -TaskName "KGRS_DB_Backup" -Trigger $trigger -Action $action -User "SYSTEM" -Settings $settings