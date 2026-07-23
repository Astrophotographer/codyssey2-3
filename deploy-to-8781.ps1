# Run ON chancelab-4090 (Windows) in PowerShell as the service owner.
# Expects this repo already copied to C:\aigraphers (or set $Root).
$ErrorActionPreference = "Stop"
$Root = if ($env:AIGRAPHERS_ROOT) { $env:AIGRAPHERS_ROOT } else { "C:\aigraphers" }
$Port = 8781
Set-Location $Root

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
  py -3 -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Free port 8781 (uvicorn / old python / nginx listener if bound here)
Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Prefer matching existing process manager if present; otherwise start detached uvicorn
$cmd = "$Root\.venv\Scripts\python.exe -m app.main"
Start-Process -FilePath "$Root\.venv\Scripts\python.exe" -ArgumentList "-m","app.main" -WorkingDirectory $Root -WindowStyle Hidden

Start-Sleep -Seconds 2
try {
  $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/login" -UseBasicParsing -TimeoutSec 5
  Write-Host "OK /login => $($r.StatusCode)"
} catch {
  Write-Host "WARN: local /login check failed: $_"
}
Write-Host "Public check: curl http://100.119.70.25:8781/login"
