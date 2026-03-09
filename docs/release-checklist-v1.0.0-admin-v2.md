# Release Checklist - v1.0.0 + Admin UI v2

## 1) Environment & Service
- [ ] Backend is running at `http://127.0.0.1:8000`
- [ ] Admin frontend is running at `http://127.0.0.1:5174`
- [ ] Mobile frontend is running at `http://127.0.0.1:5173`
- [ ] Login works with valid admin account

## 2) Core User Flow
- [ ] Login gate works (not logged in cannot access main workspace)
- [ ] Left menu shows 4 entries only:
  - [ ] Dashboard
  - [ ] User & System
  - [ ] Asset Management
  - [ ] Advanced Tools
- [ ] Logout returns to login page

## 3) Dashboard (panel-dashboard)
- [ ] Manual refresh works
- [ ] Auto/manual toggle works
- [ ] Live status + last-updated timestamp updates correctly
- [ ] KPI values update correctly
- [ ] CPU/MEM/DISK bars update correctly
- [ ] CPU/MEM/DISK sparklines render correctly
- [ ] Abnormal table filter by status works
- [ ] Abnormal table keyword filter works
- [ ] Export abnormal CSV works
- [ ] Local collect action works

## 4) User & System (panel-user-system)
- [ ] Create user works
- [ ] List users works
- [ ] Create system works
- [ ] List systems works
- [ ] Error and success messages follow unified format

## 5) Asset Management (panel-assets)
- [ ] Create asset works
- [ ] List assets works
- [ ] Asset filter fields work
- [ ] Export asset CSV works
- [ ] Batch import works
- [ ] Error and success messages follow unified format

## 6) Advanced Tools (panel-tools-ai)
- [ ] Tool tabs are visible and switchable
- [ ] Last selected tool tab is remembered after reload

### 6.1 Ops Approval
- [ ] Tool task list works
- [ ] Tool task status update works

### 6.2 AI Diagnosis
- [ ] Diagnosis list works with severity filter

### 6.3 Template & Snapshot
- [ ] Create template works
- [ ] List templates works
- [ ] Create snapshot works

### 6.4 Rules & Audit
- [ ] Load/save rules works
- [ ] Audit filter query works

### 6.5 Debug & Error Codes
- [ ] Error code guide visible
- [ ] Request history refresh/clear works

## 7) API Smoke Validation
- [ ] `/api/v1/monitoring/overview`
- [ ] `/api/v1/admin/assets/summary`
- [ ] `/api/v1/admin/users`
- [ ] `/api/v1/admin/systems`
- [ ] `/api/v1/toolbox/tasks`

Reference artifacts:
- `/tmp/aegis_verify_monitoring.json`
- `/tmp/aegis_verify_asset_summary.json`
- `/tmp/aegis_verify_users.json`
- `/tmp/aegis_verify_systems.json`
- `/tmp/aegis_verify_tool_tasks.json`

## 8) Docs & Handover
- [ ] README includes Admin v2 usage guide
- [ ] `docs/admin-ui-optimization-summary-2026-03-01.md` is up-to-date
- [ ] This checklist is attached in release handover

## 9) Rollback Plan (if needed)
- [ ] Checkout previous stable commit
- [ ] Restart frontend services
- [ ] Re-run smoke script: `./scripts/iteration3_smoke.sh`
