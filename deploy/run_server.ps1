# ============================================================================
#  run_server.ps1 — start the incident-response API server (Windows)
# ----------------------------------------------------------------------------
#  Usage (from the repo root, after deploy\setup_server.ps1):
#      powershell -ExecutionPolicy Bypass -File deploy\run_server.ps1
#      powershell -ExecutionPolicy Bypass -File deploy\run_server.ps1 -OpenFirewall
#      powershell -ExecutionPolicy Bypass -File deploy\run_server.ps1 -Port 9000
#
#  -OpenFirewall adds a Windows Firewall inbound rule for the port so other
#  machines on your LAN can reach the server (needs an elevated/admin shell).
#  Ctrl+C stops the server. Paused (HITL) runs survive restarts via the
#  SQLite checkpointer.
# ============================================================================

param(
    [int]$Port = 8000,
    [string]$BindHost = "0.0.0.0",
    [switch]$OpenFirewall
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: no .env found. Run deploy\setup_server.ps1 first." -ForegroundColor Red
    exit 1
}

if ($OpenFirewall) {
    $ruleName = "IncidentResponse-API-$Port"
    $existing = netsh advfirewall firewall show rule name=$ruleName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Adding firewall rule '$ruleName' (requires admin)..." -ForegroundColor Yellow
        netsh advfirewall firewall add rule name=$ruleName dir=in action=allow protocol=TCP localport=$Port
    } else {
        Write-Host "Firewall rule '$ruleName' already exists." -ForegroundColor Green
    }
}

# Show every LAN address clients can use.
Write-Host "`n== Incident Response API server ==" -ForegroundColor Cyan
$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -ExpandProperty IPAddress
foreach ($ip in $ips) {
    Write-Host "  Reachable at:  http://${ip}:$Port   (docs: http://${ip}:$Port/docs)" -ForegroundColor Green
}
Write-Host "  Health check:  http://localhost:$Port/health"
Write-Host "  Stop with Ctrl+C.`n"

uv run uvicorn server.app:app --host $BindHost --port $Port
