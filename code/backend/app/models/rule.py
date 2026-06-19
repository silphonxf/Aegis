from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StatusRule(Base):
    __tablename__ = "status_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpu_warn: Mapped[int] = mapped_column(Integer, default=70)
    cpu_critical: Mapped[int] = mapped_column(Integer, default=90)
    mem_warn: Mapped[int] = mapped_column(Integer, default=75)
    mem_critical: Mapped[int] = mapped_column(Integer, default=90)
    disk_warn: Mapped[int] = mapped_column(Integer, default=80)
    disk_critical: Mapped[int] = mapped_column(Integer, default=95)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
