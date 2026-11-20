###############################################################################
# VulnCastle - Lab Startup Script (Windows PowerShell)
###############################################################################

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "+==============================================+" -ForegroundColor Cyan
Write-Host "|           VulnCastle Lab Environment         |" -ForegroundColor Cyan
Write-Host "|   Intentionally Vulnerable - Training Only   |" -ForegroundColor Cyan
Write-Host "+==============================================+" -ForegroundColor Cyan
Write-Host ""

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker is not installed." -ForegroundColor Red
    Write-Host "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
}

# Check Docker Compose
try {
    docker compose version | Out-Null
} catch {
    Write-Host "[ERROR] Docker Compose (v2) is not available." -ForegroundColor Red
    exit 1
}

# Check Docker daemon
try {
    docker info 2>$null | Out-Null
} catch {
    Write-Host "[ERROR] Docker daemon is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Building base image..." -ForegroundColor Yellow
docker build -t vulncastle-base:latest ./lab/base/

Write-Host "[*] Building and starting all services..." -ForegroundColor Yellow
docker compose up -d --build

Write-Host ""
Write-Host "[+] VulnCastle is running!" -ForegroundColor Green
Write-Host ""
Write-Host "=== DMZ Network (attacker-accessible) ===" -ForegroundColor Cyan
Write-Host "  Web Portal  : http://localhost:8080"
Write-Host "  Webmail     : http://localhost:8025"
Write-Host "  SSH Gateway : ssh -p 2222 sysadmin@localhost (pass: admin123)"
Write-Host ""
Write-Host "=== Internal Network (pivot required) ===" -ForegroundColor Cyan
Write-Host "  API Server  : app-01    (10.10.0.13:3000)"
Write-Host "  Database    : db-01     (10.10.0.14:3306)"
Write-Host "  File Share  : file-01   (10.10.0.15:445)"
Write-Host "  Admin Panel : admin-01  (10.10.0.16:8080)"
Write-Host ""
Write-Host "[!] This environment is intentionally vulnerable." -ForegroundColor Yellow
Write-Host "    DO NOT expose to untrusted networks." -ForegroundColor Yellow
