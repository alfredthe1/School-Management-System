# Start Django development server (SQLite, DEBUG mode).
# Usage: .\scripts\run-dev.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "venv\Scripts\python.exe"

$env:DJANGO_ENV = "development"
$env:DJANGO_DEBUG = "True"

Set-Location $projectRoot

Write-Host ""
Write-Host "Happy Child School - development server" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Demo: admin/admin123, teacher1/teacher123, parent1/parent123" -ForegroundColor Gray
Write-Host ""
Write-Host "Mobile testing:" -ForegroundColor Yellow
Write-Host "  LAN:   .\scripts\start-lan.ps1" -ForegroundColor Gray
Write-Host "  ngrok: .\scripts\start-ngrok.ps1  (Django must already be running)" -ForegroundColor Gray
Write-Host ""

& $python manage.py runserver