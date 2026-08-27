# ============================================================================
#  send_test_incident.ps1 — exercise the live server from another machine
# ----------------------------------------------------------------------------
#  Usage (from any PC on the LAN):
#      powershell -ExecutionPolicy Bypass -File deploy\send_test_incident.ps1 -Server http://192.168.1.50:8000
#      ... -ApiKey "your-key"          # if SERVER_API_KEY is set on the server
#      ... -Hitl approve               # auto-answer if the run pauses for review
#
#  Submits a sample alert, polls until the run finishes or pauses at the
#  human-review checkpoint, optionally applies the HITL decision, then prints
#  the resolution and audit-trail summary.
# ============================================================================

param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$ApiKey = "",
    [ValidateSet("", "approve", "reject")][string]$Hitl = "",
    [string]$IncidentId = "INC-LIVE-$(Get-Date -Format 'HHmmss')"
)

$ErrorActionPreference = "Stop"
$headers = @{}
if ($ApiKey) { $headers["X-API-Key"] = $ApiKey }

Write-Host "== Live server test against $Server ==" -ForegroundColor Cyan

# 1. Health
$health = Invoke-RestMethod -Uri "$Server/health" -Headers $headers
Write-Host ("health: {0} | provider: {1} | mode: {2} | auth: {3}" -f `
    $health.status, $health.llm_provider, $health.run_mode, $health.auth) -ForegroundColor Green

# 2. Submit a sample alert
$alert = @{
    incident_id         = $IncidentId
    service_name        = "checkout"
    metric              = "error_rate"
    threshold_violation = "34% > 5%"
    timestamp           = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json

Write-Host "`nSubmitting incident $IncidentId..." -ForegroundColor Cyan
$submitted = Invoke-RestMethod -Uri "$Server/incidents" -Method Post -Body $alert `
    -ContentType "application/json" -Headers $headers
Write-Host "accepted: $($submitted | ConvertTo-Json -Compress)"

# 3. Poll until it completes, pauses, or errors
$record = $null
foreach ($i in 1..120) {
    Start-Sleep -Seconds 2
    $record = Invoke-RestMethod -Uri "$Server/incidents/$IncidentId" -Headers $headers
    Write-Host ("  [{0,3}s] status={1}" -f ($i * 2), $record.status)
    if ($record.status -ne "running") { break }
}

# 4. HITL checkpoint
if ($record.status -eq "paused_human_review") {
    Write-Host ("`nPAUSED for human review — hypothesis: '{0}' (confidence {1}, severity {2})" -f `
        $record.root_cause_hypothesis, $record.root_cause_confidence, $record.severity) -ForegroundColor Yellow
    $decision = $Hitl
    if (-not $decision) { $decision = Read-Host "Decision (approve/reject)" }
    Invoke-RestMethod -Uri "$Server/incidents/$IncidentId/hitl" -Method Post `
        -Body (@{ decision = $decision } | ConvertTo-Json) -ContentType "application/json" `
        -Headers $headers | Out-Null
    Write-Host "applied: $decision — waiting for completion..."
    foreach ($i in 1..60) {
        Start-Sleep -Seconds 2
        $record = Invoke-RestMethod -Uri "$Server/incidents/$IncidentId" -Headers $headers
        if ($record.status -ne "running") { break }
    }
}

# 5. Final result + audit trail
Write-Host "`n== RESULT ==" -ForegroundColor Cyan
Write-Host ("status={0}  resolution={1}  severity={2}  confidence={3}  steps={4}" -f `
    $record.status, $record.resolution, $record.severity, `
    $record.root_cause_confidence, $record.total_steps) -ForegroundColor Green
if ($record.status -eq "error") { Write-Host "error: $($record.error)" -ForegroundColor Red }

$audit = Invoke-RestMethod -Uri "$Server/incidents/$IncidentId/audit" -Headers $headers
Write-Host "`naudit trail ($($audit.events.Count) events, source=$($audit.source)):"
foreach ($e in $audit.events) {
    Write-Host ("  step {0,2}: {1,-24} {2}" -f $e.step_number, $e.node_name, $e.decision)
}
