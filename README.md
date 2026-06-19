# Aegis Codex Workspace

This is the curated Codex workspace for Aegis. It keeps the files that are useful for editing, review, and upload: source code, essential scripts, core documents, and agent context.

## Layout

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

## What Was Kept

- Core backend, admin frontend, and mobile frontend code.
- Backend migrations, tests, dependency files, Dockerfile, and environment examples.
- Minimal development scripts needed for startup, status, stop, and HTTPS static serving.
- Core API, milestone, design, and database documents.
- Root Markdown files for quick editing and agent handoff.

## What Was Excluded

- Git history from the OpenClaw project.
- Virtual environments and dependency caches.
- Runtime logs, certificates, local databases, uploads, and generated reports.
- Optional scripts for smoke tests, offline AI setup, server deployment, and context sync.
- Temporary progress documents and generated inventory documents.

## Original Project

```text
/home/xf/.openclaw/workspace/projects/Aegis
```

The original project was checkpointed in Git before this workspace was generated.

## Start

```bash
./scripts/dev-up.sh
./scripts/dev-status.sh
```
