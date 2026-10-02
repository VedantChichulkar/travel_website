from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, event, func, inspect
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.hotel import Hotel
    from app.models.user import User


class SettlementStatus(str, Enum):
    ON_HOLD = "ON_HOLD"
    ELIGIBLE = "ELIGIBLE"
    PROCESSING = "PROCESSING"
    SETTLED = "SETTLED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class SettlementAdjustmentKind(str, Enum):
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class PayoutStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    REVERSED = "REVERSED"


class Settlement(Base):
    """One immutable financial snapshot per completed booking.

    Amounts may only be recalculated before payout processing. Once settled, later
    corrections are append-only SettlementAdjustment records.
    """

    __tablename__ = "settlements"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_settlements_booking"),
        CheckConstraint("gross_amount >= 0", name="ck_settlements_gross"),
        CheckConstraint("vayora_fee >= 0", name="ck_settlements_fee"),
        CheckConstraint("refund_deductions >= 0", name="ck_settlements_refunds"),
        CheckConstraint("net_payable >= 0", name="ck_settlements_net"),
        Index("ix_settlements_hotel_status", "hotel_id", "status"),
        Index("ix_settlements_status_eligibility", "status", "eligibility_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    commission_rule: Mapped[str | None] = mapped_column(String(120))
    vayora_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    refund_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    adjustment_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    net_payable: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    eligibility_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[SettlementStatus] = mapped_column(SqlEnum(SettlementStatus, name="settlement_status", native_enum=False), nullable=False, index=True)
    hold_reason: Mapped[str | None] = mapped_column(Text)
    held_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payout_provider: Mapped[str | None] = mapped_column(String(40))
    payout_provider_reference: Mapped[str | None] = mapped_column(String(120), unique=True)
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hotel: Mapped[Hotel] = relationship("Hotel", foreign_keys=[hotel_id])
    booking: Mapped[Booking] = relationship("Booking", foreign_keys=[booking_id])
    held_by: Mapped[User | None] = relationship("User", foreign_keys=[held_by_user_id])
    adjustments: Mapped[list[SettlementAdjustment]] = relationship(
        back_populates="settlement",
        cascade="all, delete-orphan",
        foreign_keys="SettlementAdjustment.settlement_id",
        order_by="SettlementAdjustment.id",
    )
    applied_adjustments: Mapped[list[SettlementAdjustment]] = relationship(
        foreign_keys="SettlementAdjustment.applied_to_settlement_id",
        order_by="SettlementAdjustment.id",
    )
    events: Mapped[list[SettlementEvent]] = relationship(back_populates="settlement", cascade="all, delete-orphan", order_by="SettlementEvent.id")
    payout: Mapped[Payout | None] = relationship(back_populates="settlement", uselist=False, cascade="all, delete-orphan")


class SettlementAdjustment(Base):
    """Append-only signed correction; settled snapshots are never rewritten."""

    __tablename__ = "settlement_adjustments"
    __table_args__ = (CheckConstraint("amount <> 0", name="ck_settlement_adjustments_nonzero"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlements.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind: Mapped[SettlementAdjustmentKind] = mapped_column(SqlEnum(SettlementAdjustmentKind, name="settlement_adjustment_kind", native_enum=False), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    applies_to_current_settlement: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    applied_to_settlement_id: Mapped[int | None] = mapped_column(ForeignKey("settlements.id", ondelete="RESTRICT"), index=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    settlement: Mapped[Settlement] = relationship(back_populates="adjustments", foreign_keys=[settlement_id])
    applied_to_settlement: Mapped[Settlement | None] = relationship(back_populates="applied_adjustments", foreign_keys=[applied_to_settlement_id])
    created_by: Mapped[User] = relationship("User", foreign_keys=[created_by_user_id])


class SettlementEvent(Base):
    """Append-only audit ledger for all settlement state changes."""

    __tablename__ = "settlement_events"
    __table_args__ = (Index("ix_settlement_events_settlement_created", "settlement_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlements.id", ondelete="RESTRICT"), nullable=False, index=True)
    old_status: Mapped[SettlementStatus | None] = mapped_column(SqlEnum(SettlementStatus, name="settlement_status", native_enum=False))
    new_status: Mapped[SettlementStatus] = mapped_column(SqlEnum(SettlementStatus, name="settlement_status", native_enum=False), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    settlement: Mapped[Settlement] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship("User", foreign_keys=[actor_user_id])


class Payout(Base):
    """Durable one-to-one payout instruction and provider reconciliation state."""

    __tablename__ = "payouts"
    __table_args__ = (
        UniqueConstraint("settlement_id", name="uq_payouts_settlement"),
        UniqueConstraint("idempotency_key", name="uq_payouts_idempotency"),
        UniqueConstraint("provider_payout_id", name="uq_payouts_provider_reference"),
        CheckConstraint("amount >= 0", name="ck_payouts_amount"),
        Index("ix_payouts_status_retry", "status", "next_retry_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    settlement_id: Mapped[int] = mapped_column(ForeignKey("settlements.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    beneficiary_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_fingerprint: Mapped[str | None] = mapped_column(String(64))
    provider_contact_id: Mapped[str | None] = mapped_column(String(120))
    provider_fund_account_id: Mapped[str | None] = mapped_column(String(120))
    provider_payout_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    provider_utr: Mapped[str | None] = mapped_column(String(120))
    provider_status: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[PayoutStatus] = mapped_column(SqlEnum(PayoutStatus, name="payout_status", native_enum=False), nullable=False, default=PayoutStatus.PENDING, server_default=PayoutStatus.PENDING.value, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    reconciliation_reason: Mapped[str | None] = mapped_column(Text)
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    settlement: Mapped[Settlement] = relationship(back_populates="payout")


class PayoutWebhookEvent(Base):
    """Provider callback dedupe ledger; raw sensitive payloads are never stored."""

    __tablename__ = "payout_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_payout_webhook_provider_event"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payout_id: Mapped[int | None] = mapped_column(ForeignKey("payouts.id", ondelete="SET NULL"), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


@event.listens_for(Settlement, "before_update")
def prevent_settled_snapshot_rewrite(_mapper, _connection, target: Settlement) -> None:
    """Reject ORM writes to a snapshot that was already committed as settled."""
    session = object_session(target)
    if session is None or not session.is_modified(target, include_collections=False):
        return
    history = inspect(target).attrs.status.history
    prior_status = history.deleted[0] if history.deleted else target.status
    if prior_status == SettlementStatus.SETTLED:
        changed = {attribute.key for attribute in inspect(target).attrs if attribute.history.has_changes()}
        immutable_snapshot = {
            "hotel_id", "booking_id", "currency", "gross_amount", "vayora_fee",
            "refund_deductions", "adjustment_total", "net_payable", "eligibility_date",
            "commission_rate", "commission_rule", "payout_provider",
            "payout_provider_reference", "processing_at", "settled_at",
        }
        if changed & immutable_snapshot:
            raise ValueError("Settled financial snapshots are immutable; append an adjustment or reversal")
