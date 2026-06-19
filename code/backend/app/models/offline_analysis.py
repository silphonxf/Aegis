from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OfflineAnalysisTask(Base):
    __tablename__ = "offline_analysis_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # system|manual
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="done", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OfflineAnalysisResult(Base):
    __tablename__ = "offline_analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    matched_rules: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    suggestions: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    raw_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
