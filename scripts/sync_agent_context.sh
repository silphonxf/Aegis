#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CTX_FILE="$REPO_DIR/docs/AGENT_CONTEXT.md"
MSG="${*:-同步 Aegis 上下文（无额外备注）}"
DATE="$(date +%F)"
TS="$(date '+%F %T %z')"

if [[ ! -f "$CTX_FILE" ]]; then
  echo "[ERROR] context file not found: $CTX_FILE" >&2
  exit 1
fi

python3 - "$CTX_FILE" "$DATE" "$TS" "$MSG" <<'PY'
import re, sys
path, date, ts, msg = sys.argv[1:5]
text = open(path, 'r', encoding='utf-8').read()

# 1) update header date
text = re.sub(r'^> 最后更新：.*$', f'> 最后更新：{date}  ', text, flags=re.M)

# 2) inject/update section 7 log
marker = '## 7. 最近更新记录（倒序）'
if marker in text:
    head, tail = text.split(marker, 1)
    section = marker + tail
    date_header = f'### {date}'
    if date_header in section:
        section = section.replace(date_header, f"{date_header}\n- {msg}\n- 同步时间：{ts}", 1)
    else:
        insert = f"\n\n### {date}\n- {msg}\n- 同步时间：{ts}\n"
        section = section.replace(marker, marker + insert, 1)
    text = head + section

open(path, 'w', encoding='utf-8').write(text)
PY

cd "$REPO_DIR"

git add docs/AGENT_CONTEXT.md
if git diff --cached --quiet; then
  echo "[OK] no content changes"
  exit 0
fi

BRANCH="$(git branch --show-current)"
COMMIT_MSG="docs: sync Aegis agent context"

git commit -m "$COMMIT_MSG"
git push origin "$BRANCH"

echo "[OK] synced and pushed on $BRANCH"
