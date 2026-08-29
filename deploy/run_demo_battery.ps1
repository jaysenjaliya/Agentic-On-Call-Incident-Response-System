# ============================================================================
#  run_demo_battery.ps1 — drive the seeded incident suite against a LIVE server
# ----------------------------------------------------------------------------
#  Submits incident JSONs from data/incidents/ to a running server over HTTP,
#  handles the human-review checkpoint, and prints a results table scored
#  against each incident's expected_outcome.
#
#  Usage:
#      # curated 5-incident demo (one per behaviour) — the default
#      powershell -ExecutionPolicy Bypass -File deploy\run_demo_battery.ps1 -Server http://10.200.10.201:8000
#
#      # the full 20-incident suite
#      ... -All
#
#      # pick specific ones
#      ... -Only INC-001,INC-003,INC-012
#
#  HITL policy (-Hitl):
#      runbook  approve iff a runbook matched, else reject  (default; ADR-0018)
#      approve  always approve
#      reject   always reject
#
#  Safety: refuses to run if the server reports run_mode=prod (real escalation
#  emails would be sent). Pass -AllowProd to override deliberately.
# ============================================================================

param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$ApiKey = "",
    [switch]$All,
    [string[]]$Only = @(),
    [ValidateSet("runbook", "approve", "reject")][string]$Hitl = "runbook",
    [double]$PaceSeconds = 2.0,
    [int]$TimeoutSeconds = 240,
    [switch]$AllowProd,
    [string]$IncidentDir = ""
)

$ErrorActionPreference = "Stop"
$Server = $Server.TrimEnd('/')
$headers = @{}
if ($ApiKey) { $headers["X-API-Key"] = $ApiKey }

# The curated demo set: one incident per behaviour the system is meant to show.
$curated = @("INC-001", "INC-003", "INC-013", "INC-016", "INC-018")

if (-not $IncidentDir) {
    $IncidentDir = Join-Path (Split-Path -Parent $PSScriptRoot) "data\incidents"
}

# ---- 1. Health + safety gate ------------------------------------------------
Write-Host "== Incident battery against $Server ==" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$Server/health" -Headers $headers -TimeoutSec 15
} catch {
    Write-Host "Cannot reach $Server/health - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Check: server running? firewall rule for the port? same network?" -ForegroundColor Yellow
    exit 1
}
Write-Host ("server: provider={0} model-mode={1} auth={2}" -f `
    $health.llm_provider, $health.run_mode, $health.auth) -ForegroundColor Green

if ($health.run_mode -eq "prod" -and -not $AllowProd) {
    Write-Host "`nREFUSING: server run_mode=prod - escalations would send REAL emails." -ForegroundColor Red
    Write-Host "Set RUN_MODE=mock in the server's .env and restart, or pass -AllowProd." -ForegroundColor Yellow
    exit 1
}

# ---- 2. Select incidents ----------------------------------------------------
$files = Get-ChildItem (Join-Path $IncidentDir "*.json") | Sort-Object Name
$incidents = foreach ($f in $files) { Get-Content $f.FullName -Raw | ConvertFrom-Json }

# Normalize -Only: `powershell -File ... -Only A,B` arrives as one comma-joined
# string, while a direct call passes a real array. Handle both.
$onlyIds = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } |
             Where-Object { $_ })

if ($onlyIds.Count -gt 0) {
    $incidents = $incidents | Where-Object { $onlyIds -contains $_.incident_id }
} elseif (-not $All) {
    $incidents = $incidents | Where-Object { $curated -contains $_.incident_id }
}
if (-not $incidents) { Write-Host "No incidents selected." -ForegroundColor Red; exit 1 }

Write-Host ("running {0} incident(s), HITL policy={1}, pace={2}s`n" -f `
    @($incidents).Count, $Hitl, $PaceSeconds)

# ---- 3. Run each incident ---------------------------------------------------
$results = @()
$n = 0
foreach ($inc in $incidents) {
    $n++
    # Unique id per run so re-running the battery never collides (409) with the
    # previous run's completed/paused thread on the server.
    $runId = "{0}-R{1}" -f $inc.incident_id, (Get-Date -Format 'HHmmss')
    if ($n -gt 1 -and $PaceSeconds -gt 0) { Start-Sleep -Seconds $PaceSeconds }

    $payload = @{
        incident_id         = $runId
        service_name        = $inc.service_name
        metric              = $inc.metric
        threshold_violation = $inc.threshold_violation
        timestamp           = $inc.timestamp
        description         = $inc.description
    }
    # Tool-failure incidents carry an inject_failures map; the server applies it
    # per request so the live run exercises the same chaos as the offline eval.
    $injected = ""
    if ($inc.PSObject.Properties.Name -contains 'inject_failures' -and $inc.inject_failures) {
        $map = @{}
        foreach ($p in $inc.inject_failures.PSObject.Properties) { $map[$p.Name] = $p.Value }
        $payload["inject_failures"] = $map
        $injected = ($map.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ","
    }
    $body = $payload | ConvertTo-Json -Depth 5

    $label = "[{0}/{1}] {2}  ({3}, expect {4})" -f `
        $n, @($incidents).Count, $inc.incident_id, $inc.category, $inc.expected_outcome
    if ($injected) { $label += "  [inject: $injected]" }
    Write-Host $label -ForegroundColor Cyan

    $started = Get-Date
    try {
        Invoke-RestMethod -Uri "$Server/incidents" -Method Post -Body $body `
            -ContentType "application/json" -Headers $headers -TimeoutSec 30 | Out-Null
    } catch {
        Write-Host "   submit failed: $($_.Exception.Message)" -ForegroundColor Red
        $results += [pscustomobject]@{ Incident = $inc.incident_id; Category = $inc.category
            Expected = $inc.expected_outcome; Actual = "submit_error"; Match = $false
            Confidence = $null; Steps = $null; Seconds = 0; Hitl = "" }
        continue
    }

    # Poll to a terminal state, answering the HITL checkpoint if it fires.
    $hitlUsed = ""
    $record = $null
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        $record = Invoke-RestMethod -Uri "$Server/incidents/$runId" -Headers $headers -TimeoutSec 20

        if ($record.status -eq "paused_human_review") {
            switch ($Hitl) {
                "approve" { $decision = "approve" }
                "reject"  { $decision = "reject" }
                default   { $decision = if ($record.matched_runbook_id) { "approve" } else { "reject" } }
            }
            $hitlUsed = $decision
            Write-Host ("   HITL pause (confidence {0}, runbook {1}) -> {2}" -f `
                $record.root_cause_confidence,
                $(if ($record.matched_runbook_id) { $record.matched_runbook_id } else { "none" }),
                $decision) -ForegroundColor Yellow
            Invoke-RestMethod -Uri "$Server/incidents/$runId/hitl" -Method Post `
                -Body (@{ decision = $decision } | ConvertTo-Json) `
                -ContentType "application/json" -Headers $headers -TimeoutSec 20 | Out-Null
            continue
        }
        if ($record.status -ne "running") { break }
    }

    $elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
    $actual = if ($record.status -eq "error") { "error" }
              elseif ($record.resolution) { $record.resolution }
              else { "timeout" }
    $match = ($actual -eq $inc.expected_outcome)

    $colour = if ($match) { "Green" } else { "Red" }
    Write-Host ("   -> {0} in {1}s (confidence {2}, {3} steps)" -f `
        $actual, $elapsed, $record.root_cause_confidence, $record.total_steps) -ForegroundColor $colour
    if ($record.status -eq "error") { Write-Host "   error: $($record.error)" -ForegroundColor Red }

    $results += [pscustomobject]@{
        Incident = $inc.incident_id; Category = $inc.category
        Expected = $inc.expected_outcome; Actual = $actual; Match = $match
        Confidence = $record.root_cause_confidence; Steps = $record.total_steps
        Seconds = $elapsed; Hitl = $hitlUsed; Injected = $injected
        FailedSources = ($record.data_sources_failed -join ",")
    }
}

# ---- 4. Scorecard -----------------------------------------------------------
Write-Host "`n== RESULTS ==" -ForegroundColor Cyan
$results | Format-Table Incident, Category, Expected, Actual, Match, Confidence, Steps, Seconds, Hitl, Injected, FailedSources -AutoSize

$matched = @($results | Where-Object { $_.Match }).Count
$total = @($results).Count
$pct = if ($total) { [math]::Round(100 * $matched / $total, 1) } else { 0 }
Write-Host ("matched expected outcome: {0}/{1} ({2}%)" -f $matched, $total, $pct) `
    -ForegroundColor $(if ($matched -eq $total) { "Green" } else { "Yellow" })

$dlq = Invoke-RestMethod -Uri "$Server/dlq" -Headers $headers -TimeoutSec 20
Write-Host ("dead letter queue: {0} entr{1}" -f @($dlq).Count, $(if (@($dlq).Count -eq 1) { "y" } else { "ies" }))

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = Join-Path (Split-Path -Parent $PSScriptRoot) "evaluation\live_battery_$stamp.json"
$results | ConvertTo-Json -Depth 4 | Set-Content $out -Encoding utf8
Write-Host "saved: $out"
