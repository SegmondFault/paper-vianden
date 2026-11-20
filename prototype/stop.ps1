###############################################################################
# VulnCastle - Lab Shutdown Script (Windows PowerShell)
###############################################################################
Write-Host "[*] Stopping VulnCastle lab..." -ForegroundColor Yellow
docker compose down
Write-Host "[+] Lab stopped." -ForegroundColor Green
