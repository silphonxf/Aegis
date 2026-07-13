from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIEngineConfig(Base):
    __tablename__ = "ai_engine_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    engine_type: Mapped[str] = mapped_column(String(32), nullable=False, default="offline")
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    chat_path: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    diagnose_path: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    log_analyze_path: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
