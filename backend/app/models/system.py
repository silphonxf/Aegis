from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class System(Base):
    __tablename__ = "systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    env: Mapped[str] = mapped_column(String(32), default="prod", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SystemStatusSnapshot(Base):
    __tablename__ = "system_status_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    host_online: Mapped[str] = mapped_column(String(16), default="unknown")
    port_ok: Mapped[str] = mapped_column(String(16), default="unknown")
    cpu_level: Mapped[str] = mapped_column(String(16), default="unknown")
    mem_level: Mapped[str] = mapped_column(String(16), default="unknown")
    disk_level: Mapped[str] = mapped_column(String(16), default="unknown")
    last_inspection_result: Mapped[str] = mapped_column(String(16), default="unknown")
    last_selfcheck_result: Mapped[str] = mapped_column(String(16), default="unknown")
    status_color: Mapped[str] = mapped_column(String(16), default="green")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
