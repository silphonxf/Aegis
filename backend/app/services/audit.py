import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    action: str,
    resource: str,
    user: User | None = None,
    detail: dict[str, Any] | None = None,
    username: str | None = None,
):
    row = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else username,
        action=action,
        resource=resource,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
    )
    db.add(row)
    db.commit()
