# Expose local Django (port 8000) via ngrok for mobile testing.
# Usage: .\scripts\start-ngrok.ps1
# Prerequisite: Django runserver already running on http://127.0.0.1:8000

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "Happy Child School - ngrok mobile tunnel" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 3
    Write-Host "[OK] Django is running on port 8000" -ForegroundColor Green
}
catch {
    Write-Host "[!] Django is not running. Start it first:" -ForegroundColor Yellow
    Write-Host "    cd $projectRoot"
    Write-Host "    .\venv\Scripts\python.exe manage.py runserver"
    exit 1
}

$publicUrl = $null
try {
    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2
    if ($tunnels.tunnels.Count -gt 0) {
        Write-Host "[i] ngrok already running - fetching public URL..." -ForegroundColor Yellow
        $publicUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1).public_url
    }
}
catch {
    # ngrok not running yet
}

if (-not $publicUrl) {
    Write-Host "[*] Starting ngrok tunnel to port 8000..." -ForegroundColor Cyan
    Start-Process -FilePath "ngrok" -ArgumentList "http", "8000" -WindowStyle Normal
    Start-Sleep -Seconds 3

    for ($i = 0; $i -lt 10; $i++) {
        try {
            $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2
            $publicUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1).public_url
            if ($publicUrl) { break }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
}

if (-not $publicUrl) {
    Write-Host "[!] Could not read ngrok URL." -ForegroundColor Red
    Write-Host "    Common fix: add your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor Yellow
    Write-Host "    ngrok config add-authtoken YOUR_TOKEN_HERE" -ForegroundColor Yellow
    Write-Host "    Then run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Open on your phone:" -ForegroundColor Green
Write-Host "  $publicUrl" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
Write-Host "Tips:" -ForegroundColor Yellow
Write-Host "  - First visit may show an ngrok warning page - tap Visit Site" -ForegroundColor Gray
Write-Host "  - Keep this PC on and Django running while testing" -ForegroundColor Gray
Write-Host "  - ngrok dashboard: http://127.0.0.1:4040" -ForegroundColor Gray
Write-Host ""
Write-Host "Demo logins: parent1/parent123, admin/admin123" -ForegroundColor Gray
Write-Host ""