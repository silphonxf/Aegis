import base64
import os
import re
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.ai_chat_file import AIChatFile
from app.models.user import User
from app.schemas.ai_chat_file import AIChatFileItem, AIChatFileUploadRequest, AIChatFileUploadResponse
from app.services.audit import log_action

router = APIRouter(prefix="/ai/files", tags=["ai-files"])

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "ai-chat"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

TEXT_LOG_EXTENSIONS = (
    "txt",
    "log",
    "out",
    "err",
    "trace",
    "access",
    "error",
    "csv",
    "tsv",
    "json",
    "jsonl",
    "ndjson",
    "md",
    "xml",
    "yaml",
    "yml",
    "conf",
    "ini",
    "properties",
)

TEXT_MIME_TOKENS = ("text", "json", "csv", "xml", "javascript", "x-ndjson", "yaml")


def _decode_text_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _decode_data_url(data_url: str) -> Tuple[bytes, Optional[str]]:
    match = re.match(r"^data:([^;]+);base64,(.+)$", data_url, re.S)
    if match:
        mime_type = match.group(1)
        content = match.group(2)
    else:
        mime_type = None
        content = data_url
    try:
        return base64.b64decode(content), mime_type
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "FILE_DECODE_FAILED", "message": f"附件解码失败: {e}"})


def _extract_text(name: str, mime_type: str, raw: bytes) -> Optional[str]:
    lowered_mime = (mime_type or "").lower()
    text_like = any(token in lowered_mime for token in TEXT_MIME_TOKENS)
    text_like = text_like or bool(re.search(rf"\.({'|'.join(TEXT_LOG_EXTENSIONS)})$", name, re.I))
    if not text_like:
        return None
    try:
        return _decode_text_bytes(raw)[:12000]
    except Exception:
        return None


@router.post("/upload", response_model=AIChatFileUploadResponse)
def upload_ai_file(
    payload: AIChatFileUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    raw, mime_from_data_url = _decode_data_url(payload.data_url)
    mime_type = mime_from_data_url or payload.type or "application/octet-stream"
    safe_name = os.path.basename(payload.name or "upload.bin")

    row = AIChatFile(
        conversation_id=payload.conversation_id,
        original_name=safe_name,
        mime_type=mime_type,
        size_bytes=len(raw),
        storage_path="",
        extracted_text=_extract_text(safe_name, mime_type, raw),
    )
    db.add(row)
    db.flush()

    ext = Path(safe_name).suffix or ".bin"
    day_dir = UPLOAD_ROOT / payload.conversation_id
    day_dir.mkdir(parents=True, exist_ok=True)
    file_path = day_dir / f"{row.id}{ext}"
    file_path.write_bytes(raw)
    row.storage_path = str(file_path)

    db.commit()
    db.refresh(row)

    log_action(
        db,
        "ai_file_upload",
        "ai",
        current_user,
        {"file_id": row.id, "conversation_id": row.conversation_id, "name": row.original_name, "size": row.size_bytes},
    )

    return AIChatFileUploadResponse(
        file=AIChatFileItem(
            file_id=row.id,
            name=row.original_name,
            type=row.mime_type,
            size=row.size_bytes,
            extracted_text=row.extracted_text,
            preview_excerpt=(row.extracted_text or "")[:300] or None,
        )
    )
