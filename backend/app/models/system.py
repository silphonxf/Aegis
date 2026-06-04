from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class System(Base):
    __tablename__ = "systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    host_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    env: Mapped[str] = mapped_column(String(32), default="prod", nullable=False)
    check_frequency: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SystemUserBinding(Base):
    __tablename__ = "system_user_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    binding_role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SystemLogConfig(Base):
    __tablename__ = "system_log_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    log_name: Mapped[str] = mapped_column(String(128), nullable=False)
    absolute_path: Mapped[str] = mapped_column(String(500), nullable=False)
    log_level: Mapped[str] = mapped_column(String(16), default="warning", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SystemStatusSnapshot(Base):
    __tablename__ = "system_status_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    host_online: Mapped[str] = mapped_column(String(16), default="unknown")
    port_ok: Mapped[str] = mapped_column(String(16), default="unknown")
    cpu_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mem_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    disk_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cpu_level: Mapped[str] = mapped_column(String(16), default="unknown")
    mem_level: Mapped[str] = mapped_column(String(16), default="unknown")
    disk_level: Mapped[str] = mapped_column(String(16), default="unknown")
    last_inspection_result: Mapped[str] = mapped_column(String(16), default="unknown")
    last_selfcheck_result: Mapped[str] = mapped_column(String(16), default="unknown")
    status_color: Mapped[str] = mapped_column(String(16), default="green")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
