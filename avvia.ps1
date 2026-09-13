$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

.\venv\Scripts\Activate.ps1
$env:FLASK_APP = "app.py"

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback|vEthernet|WSL" } | Select-Object -First 1 -ExpandProperty IPAddress)
Write-Host "Avvio server su http://127.0.0.1:5000 (su questo PC) e http://${ip}:5000 (da telefono/altri dispositivi sulla stessa rete Wi-Fi)" -ForegroundColor Cyan
Write-Host "Ctrl+C per fermare" -ForegroundColor Cyan
flask run --host=0.0.0.0
