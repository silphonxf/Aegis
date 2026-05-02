from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InspectionPoint(Base):
    __tablename__ = "inspection_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    point_code: Mapped[str] = mapped_column(String(64), nullable=False)
    qr_content: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    point_id: Mapped[int] = mapped_column(Integer, ForeignKey("inspection_points.id"), nullable=False)
    inspector_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
