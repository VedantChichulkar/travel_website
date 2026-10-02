"""enforce immutable audit history in the database

Revision ID: f0a7c4d9e2b5
Revises: e9f6a3b8d1c4
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f0a7c4d9e2b5"
down_revision: str | None = "e9f6a3b8d1c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    op.execute(
        "CREATE TRIGGER audit_logs_prevent_update BEFORE UPDATE ON audit_logs "
        "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit history is immutable'"
    )
    op.execute(
        "CREATE TRIGGER audit_logs_prevent_delete BEFORE DELETE ON audit_logs "
        "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit history is immutable'"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    op.execute("DROP TRIGGER IF EXISTS audit_logs_prevent_delete")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_prevent_update")
