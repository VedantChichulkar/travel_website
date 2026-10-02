"""add transactional room inventory holds and commitment counters

Revision ID: 7d8e4a0c1b9f
Revises: 2e912aca57bc
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7d8e4a0c1b9f"
down_revision: Union[str, Sequence[str], None] = "2e912aca57bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("room_inventory", sa.Column("confirmed_inventory", sa.Integer(), server_default="0", nullable=False))
    op.add_column("room_inventory", sa.Column("held_inventory", sa.Integer(), server_default="0", nullable=False))
    op.drop_constraint("ck_room_inventory_allocations", "room_inventory", type_="check")
    op.create_check_constraint(
        "ck_room_inventory_allocations",
        "room_inventory",
        "available_inventory + blocked_inventory + confirmed_inventory + held_inventory <= total_inventory",
    )
    op.create_table(
        "inventory_holds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hold_token", sa.String(length=64), nullable=False),
        sa.Column("hotel_id", sa.Integer(), nullable=False),
        sa.Column("room_type_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("check_out > check_in", name="ck_inventory_holds_stay_dates"),
        sa.CheckConstraint("rooms >= 1", name="ck_inventory_holds_rooms"),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_type_id"], ["room_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hold_token"),
    )
    op.create_index("ix_inventory_holds_hotel_id", "inventory_holds", ["hotel_id"])
    op.create_index("ix_inventory_holds_room_type_id", "inventory_holds", ["room_type_id"])
    op.create_index("ix_inventory_holds_user_id", "inventory_holds", ["user_id"])
    op.create_index("ix_inventory_holds_expires_at", "inventory_holds", ["expires_at"])
    op.create_index("ix_inventory_holds_status", "inventory_holds", ["status"])
    op.create_index("ix_inventory_holds_room_status_expiry", "inventory_holds", ["room_type_id", "status", "expires_at"])
    op.create_index("ix_inventory_holds_hotel_status", "inventory_holds", ["hotel_id", "status"])


def downgrade() -> None:
    for name in ("ix_inventory_holds_hotel_status", "ix_inventory_holds_room_status_expiry", "ix_inventory_holds_status", "ix_inventory_holds_expires_at", "ix_inventory_holds_user_id", "ix_inventory_holds_room_type_id", "ix_inventory_holds_hotel_id"):
        op.drop_index(name, table_name="inventory_holds")
    op.drop_table("inventory_holds")
    op.drop_constraint("ck_room_inventory_allocations", "room_inventory", type_="check")
    op.create_check_constraint("ck_room_inventory_allocations", "room_inventory", "available_inventory + blocked_inventory <= total_inventory")
    op.drop_column("room_inventory", "held_inventory")
    op.drop_column("room_inventory", "confirmed_inventory")
