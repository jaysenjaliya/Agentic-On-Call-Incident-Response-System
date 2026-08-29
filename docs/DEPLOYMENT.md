# Deployment — Live Server on a LAN PC

How to run the incident-response system as a real HTTP server on a second
Windows PC and drive it from any machine on your network. The server layer
(`server/` + `deploy/`) is an extension on top of the locked v1.0.0
architecture — it wraps the supervisor graph without modifying it
(ADR-0019; PRD_CHANGES.md row C-12).

## Architecture

```
your PC (client)                        spare PC (server)
────────────────                        ─────────────────────────────
deploy\send_test_incident.ps1  ──HTTP──►  uvicorn ► FastAPI (server/app.py)
curl / browser /docs                        │
                                            ▼ thread pool
                                        supervisor graph (unchanged v1.0.0)
                                        SQLite checkpointer ► HITL pause/resume
                                        data/audit_trail/ · data/dlq/
```

## API

| Method & path                  | Purpose |
|--------------------------------|---------|
| `GET /`                        | redirects to `/docs` |
| `GET /health`                  | liveness + provider / run-mode / auth info |
| `POST /incidents`              | submit an alert JSON → `202`, runs in background |
| `GET /incidents`               | list all incidents this server has handled |
| `GET /incidents/{id}`          | status + result (`running` / `paused_human_review` / `completed` / `error`) |
| `POST /incidents/{id}/hitl`    | `{"decision": "approve"\|"reject"}` for a paused run |
| `GET /incidents/{id}/audit`    | full audit trail (file for finished runs, checkpoint for paused) |
| `GET /dlq`                     | dead letter queue contents |
| `GET /docs`                    | interactive Swagger UI |

If `SERVER_API_KEY` is set in the server's `.env`, every request must send it
as an `X-API-Key` header. Leave it unset for open access on a trusted LAN.

## Server PC setup (one time)

On the spare Windows PC:

```powershell
git clone https://github.com/jaysenjaliya/Agentic-On-Call-Incident-Response-System.git
cd Agentic-On-Call-Incident-Response-System
powershell -ExecutionPolicy Bypass -File deploy\setup_server.ps1
```

The script installs `uv` if needed, syncs the venv with the `server` extra,
creates `.env` from the template, and runs the offline smoke checks.
**Then edit `.env`** and set:

- `GROQ_API_KEY` (or switch `LLM_PROVIDER=openai` + `OPENAI_API_KEY`)
- keep `RUN_MODE=mock` unless you want real Gmail escalation emails
- optional `SERVER_API_KEY=<secret>` to require the header

## Start the server

```powershell
# admin shell recommended the first time so the firewall rule can be added
powershell -ExecutionPolicy Bypass -File deploy\run_server.ps1 -OpenFirewall
```

It prints the LAN URLs (e.g. `http://192.168.1.50:8000`). Defaults: port 8000,
bind `0.0.0.0`. Stop with Ctrl+C — paused HITL runs survive restarts via the
SQLite checkpointer (`checkpoints/incident_checkpoints.sqlite`).

## Test it from your main PC

```powershell
powershell -ExecutionPolicy Bypass -File deploy\send_test_incident.ps1 -Server http://<server-ip>:8000
```

The script health-checks, submits a sample checkout alert, polls, prompts you
for approve/reject if the run pauses at human review, and prints the final
resolution + audit trail. Or drive it by hand:

```powershell
$s = "http://<server-ip>:8000"
Invoke-RestMethod "$s/health"
Invoke-RestMethod "$s/incidents" -Method Post -ContentType "application/json" -Body (@{
    incident_id = "INC-LIVE-1"; service_name = "checkout"
    metric = "error_rate"; threshold_violation = "34% > 5%"
} | ConvertTo-Json)
Invoke-RestMethod "$s/incidents/INC-LIVE-1"            # poll status
Invoke-RestMethod "$s/incidents/INC-LIVE-1/hitl" -Method Post -ContentType "application/json" `
    -Body '{"decision": "approve"}'                     # only if paused
Invoke-RestMethod "$s/incidents/INC-LIVE-1/audit"
```

Or just open `http://<server-ip>:8000/` in a browser — it lands on the Swagger UI.

## Run the seeded incident suite against the live server

`deploy/run_demo_battery.ps1` submits the incidents in `data/incidents/` over
HTTP, answers the human-review checkpoint, and scores each run against its
`expected_outcome`:

```powershell
# curated 5-incident demo — one per behaviour (default)
powershell -ExecutionPolicy Bypass -File deploy\run_demo_battery.ps1 -Server http://<server-ip>:8000

powershell -ExecutionPolicy Bypass -File deploy\run_demo_battery.ps1 -Server http://<server-ip>:8000 -All
... -Only INC-001,INC-018        # specific incidents
... -Hitl approve                # HITL policy: runbook (default) | approve | reject
```

The default HITL policy mirrors ADR-0018 — approve only when a runbook matched,
otherwise reject. Results print as a table and save to
`evaluation/live_battery_<timestamp>.json` (git-ignored). The script **refuses
to run against a server with `run_mode=prod`** (real escalation emails) unless
you pass `-AllowProd`.

## Injecting tool failures on a live run

The point of the system is surviving broken dependencies, so any alert may
carry an `inject_failures` map — the live equivalent of the evaluation
harness's chaos switch (ADR-0021):

```powershell
Invoke-RestMethod "$s/incidents" -Method Post -ContentType "application/json" -Body (@{
    incident_id     = "INC-CHAOS-1"; service_name = "orders-api"
    metric          = "error_rate";  threshold_violation = "34% > 5%"
    inject_failures = @{ runbooks = "timeout" }
} | ConvertTo-Json)
```

- **sources:** `logs`, `metrics`, `runbooks`, `deployments`
- **modes:** `timeout`, `rate_limit`, `auth`, `empty`, `malformed`
- unknown source or mode → `422`

The response record reports `data_sources_failed`, so you can see degradation
directly. Two behaviours worth demoing (both verified live):

| Injection | What happens |
|-----------|--------------|
| `{"metrics": "timeout"}` | metrics die, logs survive → proceeds on partial data → **resolved** (NFR-4 graceful degradation) |
| `{"runbooks": "timeout"}` | no runbook match → confidence falls to ~0.7 → **pauses for human review** → reject → **escalated** |
| `{"logs": "timeout", "metrics": "timeout"}` | all diagnosis sources dead → **escalated** without guessing |

## Troubleshooting

- **Connection refused / timeout from the other PC** → in order of likelihood:
  1. **Different subnets on an institutional network.** Check both machines'
     IPs (`ipconfig`). If they differ beyond the last octet (e.g. `10.200.10.x`
     vs `10.200.17.x`) on a campus/office network, client isolation is blocking
     you and no firewall change will help. **Fix: tether both PCs to a phone
     hotspot** — they land on the same subnet and it works immediately. (The
     server's IP changes on the new network; `run_server.ps1` prints it.)
  2. **Windows Firewall.** Re-run `run_server.ps1 -OpenFirewall` from an
     *admin* PowerShell.
  3. **Network profile set to Public**, which blocks inbound by default:
     `Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private`
- **`root cause undetermined (LLM error: NotFoundError)` in results** → the
  Groq model in `.env` was decommissioned; set `GROQ_MODEL` to a model listed
  by your account (current default: `qwen/qwen3.8-27b`, ADR-0020). The pipeline
  still terminates safely (escalates) when the LLM fails — that's by design.
- **401 responses** → the server has `SERVER_API_KEY` set; send the
  `X-API-Key` header.
- **409 on submit** → that `incident_id` is still running or paused; use a new
  id or resolve the paused run first.

## Scope notes

- LAN only by design — do not port-forward this to the internet as-is.
- The server executes at most 2 incidents concurrently (thread pool); plenty
  for testing, intentionally conservative for the shared SQLite checkpointer.
