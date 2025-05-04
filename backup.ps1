$backupDir = "D:\Code\python\KGRS\backups"
$dateStr = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Path .\db.sqlite3 -Destination "$backupDir\db_$dateStr.sqlite3"