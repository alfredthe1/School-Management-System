# Same-WiFi mobile testing — no ngrok required.
# Usage: .\scripts\start-lan.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "venv\Scripts\python.exe"

$lanIp = (
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike '127.*' -and
        $_.PrefixOrigin -ne 'WellKnown' -and
        ($_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*')
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
)

if (-not $lanIp) {
    $lanIp = (ipconfig | Select-String 'IPv4' | Select-Object -First 1) -replace '.*:\s*', ''
}

Write-Host ""
Write-Host "Happy Child School - LAN mobile access" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your PC IP: $lanIp" -ForegroundColor Yellow
Write-Host ""
Write-Host "On your phone (same Wi-Fi), open:" -ForegroundColor Green
Write-Host "  http://${lanIp}:8000" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
Write-Host "Demo logins: parent1/parent123, admin/admin123" -ForegroundColor Gray
Write-Host ""
Write-Host "Starting Django on 0.0.0.0:8000 ..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

$env:LAN_HOST = $lanIp
Set-Location $projectRoot
& $python manage.py runserver "0.0.0.0:8000"