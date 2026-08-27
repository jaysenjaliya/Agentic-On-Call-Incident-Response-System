# ============================================================================
#  setup_server.ps1 — one-time setup on the server PC (Windows)
# ----------------------------------------------------------------------------
#  Run this AFTER cloning the repo, from the repo root:
#      powershell -ExecutionPolicy Bypass -File deploy\setup_server.ps1
#  It installs uv (if missing), creates the virtualenv with server deps,
#  and scaffolds .env from the template.
# ============================================================================

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "== Agentic Incident Response — server setup ==" -ForegroundColor Cyan

# 1. uv (Python package manager)
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "uv not found — installing via astral.sh..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
uv --version

# 2. Virtualenv + dependencies (server extra = FastAPI + uvicorn)
Write-Host "`nSyncing environment (this installs Python + all deps)..." -ForegroundColor Cyan
uv sync --extra server

# 3. .env scaffold (never committed; .env is git-ignored)
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "`nCreated .env from .env.example." -ForegroundColor Yellow
    Write-Host "!! EDIT .env NOW and set your real GROQ_API_KEY (or OPENAI_API_KEY)." -ForegroundColor Red
    Write-Host "   Optional: set SERVER_API_KEY=<any-secret> to require X-API-Key on every request."
} else {
    Write-Host "`n.env already exists — leaving it untouched." -ForegroundColor Green
}

# 4. Smoke check: the pipeline's own self-tests (offline, no API key needed)
Write-Host "`nRunning offline smoke checks (--test-tools, --test-state)..." -ForegroundColor Cyan
uv run python main.py --test-tools
uv run python main.py --test-state

Write-Host "`nSetup complete. Next:" -ForegroundColor Green
Write-Host "  1. Edit .env (API key!)"
Write-Host "  2. Start the server:  powershell -ExecutionPolicy Bypass -File deploy\run_server.ps1 -OpenFirewall"
