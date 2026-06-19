# Aegis Agent Guide

## Project

Aegis is an operations assistant for mobile inspection, self-check workflows, reporting, admin management, AI-assisted diagnosis, and emergency operation tooling.

This Codex workspace is a curated editing workspace. The original OpenClaw project checkpoint was committed before this workspace was generated.

Original project:

```text
/home/xf/.openclaw/workspace/projects/Aegis
```

Curated Codex workspace:

```text
/home/xf/.codex/workspace/projects/Aegis
```

## Current Structure

```text
code/
  backend/
  frontend-admin/
  frontend-mobile/
scripts/
  dev-up.sh
  dev-status.sh
  dev-stop.sh
  serve_https.py
docs/
threads/
```

## Local Startup

Use the curated script from this workspace:

```bash
./scripts/dev-up.sh
```

The script expects the same relative structure as the original project:

- backend at `code/backend`
- mobile frontend at `code/frontend-mobile`
- admin frontend at `code/frontend-admin`

If a script still references the old layout, update it in this workspace instead of changing the OpenClaw checkpoint.

## Service URLs

Local:

```text
https://127.0.0.1:8000  Backend API
https://127.0.0.1:5173  Mobile frontend
https://127.0.0.1:5174  Admin frontend
```

LAN/Tailscale reference:

```text
https://100.102.111.74:8000
https://100.102.111.74:5173
https://100.102.111.74:5174
```

Default local admin:

```text
admin / local_admin_pass_2026
```

## Git Rules

Commit only curated code, scripts, docs, and configuration examples.

Do not commit:

- virtual environments
- local `.env`
- local SQLite databases
- certificates or private keys
- logs
- upload files
- generated reports
- Python or frontend caches
- wheelhouses, archives, or deployment bundles

## Documentation Policy

Root Markdown files should stay easy to find and edit:

- `README.md`: human entry point
- `AGENT.md`: agent rules and operating context
- `workspace-map.md`: file map and retention decisions

Long-lived product, API, database, design, and milestone documents belong in `docs/`.

Temporary task progress and session handoff notes belong in `threads/`, not in `docs/`.

## Thread Policy

Create one folder per independent work thread:

```text
threads/YYYY-MM-DD-short-topic/
```

Recommended files:

```text
README.md
notes.md
todo.md
handoff.md
```
