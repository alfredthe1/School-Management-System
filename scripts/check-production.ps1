# Validate production settings before deploy.
# Usage: .\scripts\check-production.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "venv\Scripts\python.exe"

$env:DJANGO_ENV = "production"

Set-Location $projectRoot

Write-Host ""
Write-Host "Production settings check" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

& $python manage.py check --deploy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[OK] Django deploy checks passed." -ForegroundColor Green
Write-Host "Next: collectstatic, migrate, start gunicorn (see docs/DEPLOYMENT.md)" -ForegroundColor Gray
Write-Host ""