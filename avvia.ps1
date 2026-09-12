$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

.\venv\Scripts\Activate.ps1
$env:FLASK_APP = "app.py"

Write-Host "Avvio server su http://127.0.0.1:5000 (Ctrl+C per fermare)" -ForegroundColor Cyan
flask run
