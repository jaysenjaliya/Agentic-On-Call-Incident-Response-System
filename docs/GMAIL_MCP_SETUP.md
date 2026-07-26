# Gmail MCP Setup (WI-32 — real escalation emails)

This wires the agent's `escalate` node to send a **real email** through a Gmail
**MCP server**, satisfying the PRD's "at least one real MCP tool (Gmail)"
requirement. Until you finish these steps, the system uses the mock notifier
(nothing is sent) — so the pipeline works regardless.

**Prerequisites already met on this machine:** Node.js v22 + `npx`, and the
`langchain-mcp-adapters` Python package.

We use the community server **`@gongrzhe/server-gmail-autoauth-mcp`** (runs via
`npx`, handles Google OAuth locally). You can swap servers later via the
`GMAIL_MCP_*` env vars.

---

## Step 1 — Create Google OAuth credentials (one-time, ~5 min)

1. Go to <https://console.cloud.google.com/> and create (or pick) a project.
2. **APIs & Services → Library →** search **"Gmail API" → Enable**.
3. **APIs & Services → OAuth consent screen:**
   - User type: **External** → Create.
   - Fill app name + your email where required; **Save and Continue**.
   - **Audience/Test users → Add users →** add **your own Gmail address**
     (required so the app can send as you while it's in "testing").
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID:**
   - Application type: **Desktop app** → Create.
   - **Download JSON.** Rename it to **`gcp-oauth.keys.json`**.

## Step 2 — Authenticate the MCP server (one-time)

The gongrzhe server looks for the keys and stores a token under `~/.gmail-mcp/`.

```bash
# Windows (Git Bash): create the config dir and drop the keys file in it
mkdir -p "$HOME/.gmail-mcp"
mv /path/to/gcp-oauth.keys.json "$HOME/.gmail-mcp/gcp-oauth.keys.json"

# Run the one-time browser auth flow
npx -y @gongrzhe/server-gmail-autoauth-mcp auth
```

A browser opens → sign in with the Gmail account you added as a test user →
grant "send email" access. On success it writes `~/.gmail-mcp/credentials.json`.

## Step 3 — Turn it on in `.env`

```dotenv
RUN_MODE=prod
GMAIL_MCP_ENABLED=true
ESCALATION_EMAIL_TO=your-real-inbox@example.com   # where escalations should land
# Optional overrides (defaults shown):
# GMAIL_MCP_COMMAND=npx
# GMAIL_MCP_ARGS=-y @gongrzhe/server-gmail-autoauth-mcp
# GMAIL_MCP_SEND_TOOL=send_email
```

## Step 4 — Verify a real send

```bash
# Sends a real escalation email (INC-003 is a P0 → always escalates):
uv run python main.py data/incidents/incident_003.json
```

You should receive the escalation email at `ESCALATION_EMAIL_TO`, and the run's
audit trail (`data/audit_trail/INC-003_audit.json`) will show the `escalate` node
using `MockNotificationService` → replaced by the Gmail MCP channel.

---

## How it works in the code

- [utils/notifier.py](../utils/notifier.py) `get_notifier()` returns
  `GmailMCPNotifier` when `RUN_MODE=prod` + `GMAIL_MCP_ENABLED=true`, else the mock.
- [utils/gmail_mcp.py](../utils/gmail_mcp.py) `GmailMCPNotifier.send()` spawns the
  MCP server via `MultiServerMCPClient`, finds the `send_email` tool, and invokes it.
- The `escalate` node calls `notifier.send(...)` inside try/except — if Gmail MCP
  fails, the incident **still** escalates and the error is recorded (never stranded).

## Troubleshooting

- **`send_email` not found** → the error lists the server's actual tool names; set
  `GMAIL_MCP_SEND_TOOL` to the right one.
- **Auth errors / 403** → re-run Step 2; ensure your Gmail is a Test user on the
  consent screen.
- **`npx` can't find the package** → run `npx -y @gongrzhe/server-gmail-autoauth-mcp`
  once manually to let it install.
- **Don't want to send real email yet** → set `GMAIL_MCP_ENABLED=false`; the mock
  path is the PRD-sanctioned fallback.
