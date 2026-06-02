from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    room_name: Mapped[str] = mapped_column(String(128), nullable=False)
    building: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    floor: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location_detail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class EmergencyHost(Base):
    __tablename__ = "emergency_hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    host_name: Mapped[str] = mapped_column(String(128), nullable=False)
    host_ip: Mapped[str] = mapped_column(String(120), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(32), nullable=False)
    password_ciphertext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    private_key_ciphertext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    private_key_passphrase_ciphertext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connect_timeout_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    system_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("systems.id"), nullable=True)
    room_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=True)
    asset_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("assets.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Runbook(Base):
    __tablename__ = "runbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runbook_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    runbook_name: Mapped[str] = mapped_column(String(128), nullable=False)
    runbook_type: Mapped[str] = mapped_column(String(32), nullable=False)
    system_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("systems.id"), nullable=True)
    target_host_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emergency_hosts.id"), nullable=True)
    script_type: Mapped[str] = mapped_column(String(32), nullable=False)
    script_body: Mapped[str] = mapped_column(Text, nullable=False)
    confirm_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
