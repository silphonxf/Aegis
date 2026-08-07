from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FirewallBlockConfig(Base):
    __tablename__ = "firewall_block_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_code: Mapped[str] = mapped_column(String(64), default="test-primary", nullable=False, unique=True)
    target_name: Mapped[str] = mapped_column(String(128), default="山石测试设备", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_test_target: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scheme: Mapped[str] = mapped_column(String(16), default="https", nullable=False)
    firewall_ip: Mapped[str] = mapped_column(String(128), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=443, nullable=False)
    address_book_name: Mapped[str] = mapped_column(String(128), nullable=False)
    username_encrypted: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    password_encrypted: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    addrbook_path: Mapped[str] = mapped_column(String(128), default="/api/addrbook", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
