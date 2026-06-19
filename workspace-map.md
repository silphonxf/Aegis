# Aegis Workspace Map

## Paths

| Type | Path |
| --- | --- |
| Curated Codex workspace | `/home/xf/.codex/workspace/projects/Aegis` |
| Original OpenClaw project | `/home/xf/.openclaw/workspace/projects/Aegis` |

## Retained Files

### Code

```text
code/backend/
code/frontend-admin/
code/frontend-mobile/
```

The code remains separated by runtime boundary. It is grouped under `code/` for easier navigation without flattening imports or relative asset paths.

### Scripts

```text
scripts/dev-up.sh
scripts/dev-status.sh
scripts/dev-stop.sh
scripts/serve_https.py
```

These are the minimal practical scripts for local development. `dev-up.sh` depends on `serve_https.py`.

### Documents

```text
docs/api-spec-v1.md
docs/er-model.md
docs/phase1-development-plan.md
docs/aegis-assistant-v1-development-plan.md
docs/emergency-ops-admin-design.md
docs/system-status-management-design.md
docs/shared-data-model-v1.md
docs/shared-data-migration-plan-v1.md
docs/deployment-update-manual.md
```

These documents cover API, database model, milestones, assistant design, admin design, system status design, shared data design, migration design, and update procedure.

## Excluded Files

Optional scripts were not copied:

```text
dev-check.sh
iteration3_smoke.sh
dev-reset.sh
server-up.sh
setup_offline_ai.sh
start_lan_https.sh
sync_agent_context.sh
ai_perf_check.py
```

Temporary or low-value docs were not copied:

```text
AGENT_CONTEXT.md
CONTRIBUTING.md
DOCS_INDEX.md
project-progress.md
scripts-inventory.md
login-common-pitfalls.md
integration-quickstart.md
offline-ai-setup.md
openclaw-ai-provider-design.md
openclaw-ai-adapter-local-dev.md
```

Runtime/generated files were not copied:

```text
.git/
.venv/
.logs/
.certs/
backend/.env
backend/aegis.db
backend/uploads/
backend/selfcheck_reports/
__pycache__/
.pytest_cache/
deploy/wheelhouse-py39/
deploy/*.tar.gz
```

## Thread Directory

Use `threads/` for task-specific continuation records. Keep long-lived docs in `docs/`; keep session notes and temporary progress in `threads/`.
