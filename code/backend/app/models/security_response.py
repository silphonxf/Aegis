from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FeishuUserBinding(Base):
    __tablename__ = "feishu_user_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    open_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    union_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    feishu_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    aegis_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    can_query: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_block: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class FeishuEventReceipt(Base):
    __tablename__ = "feishu_event_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IpBlockBatch(Base):
    __tablename__ = "ip_block_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="analyzed", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default="feishu", nullable=False)
    source_chat_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requester_open_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requester_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    confirmer_open_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confirmer_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    firewall_config_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("firewall_block_configs.id"),
        nullable=True,
    )
    firewall_target_code: Mapped[str] = mapped_column(String(64), default="test-primary", nullable=False)
    firewall_host: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address_book_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    jinan_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysis_json: Mapped[str] = mapped_column(Text, nullable=False)
    execution_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IpBlockItem(Base):
    __tablename__ = "ip_block_items"
    __table_args__ = (UniqueConstraint("batch_id", "ip", name="uq_ip_block_items_batch_ip"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_block_batches.id"), nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    risk_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_malicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    should_block: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_jinan_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="analyzed", nullable=False)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
