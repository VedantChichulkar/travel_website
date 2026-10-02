"""preserve audit actor identity independently of user lifecycle

Revision ID: e9f6a3b8d1c4
Revises: d8e4b1c7a2f9
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e9f6a3b8d1c4"
down_revision: str | None = "d8e4b1c7a2f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _actor_foreign_key_name() -> str | None:
    inspector = sa.inspect(op.get_bind())
    for constraint in inspector.get_foreign_keys("audit_logs"):
        if constraint.get("constrained_columns") == ["actor_user_id"]:
            return constraint.get("name")
    return None


def upgrade() -> None:
    constraint_name = _actor_foreign_key_name()
    if constraint_name:
        op.drop_constraint(constraint_name, "audit_logs", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key(
        "fk_audit_logs_actor_user_id",
        "audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
