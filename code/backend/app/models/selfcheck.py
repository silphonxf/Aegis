from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False)
    check_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SelfcheckRecord(Base):
    __tablename__ = "selfcheck_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("checklist_templates.id"), nullable=False)
    operator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class SelfcheckReport(Base):
    __tablename__ = "selfcheck_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    system_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    system_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    range_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alarm_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
