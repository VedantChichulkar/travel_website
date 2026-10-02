"""harden accounts and private verification documents

Revision ID: a5c9e3f7b2d1
Revises: f4b8d2e6a1c9
"""

from alembic import op
import sqlalchemy as sa

from app.core.sensitive_data import decrypt_sensitive, encrypt_sensitive


revision = "a5c9e3f7b2d1"
down_revision = "f4b8d2e6a1c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_index("ix_auth_sessions_revoked_at", "auth_sessions", ["revoked_at"])
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at", "expires_at"])

    op.create_table(
        "account_action_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.Enum("PASSWORD_RESET", "EMAIL_VERIFICATION", name="account_token_purpose", native_enum=False), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_account_action_tokens_token_hash"),
    )
    op.create_index("ix_account_action_tokens_user_id", "account_action_tokens", ["user_id"])
    op.create_index("ix_account_action_tokens_expires_at", "account_action_tokens", ["expires_at"])
    op.create_index("ix_account_action_tokens_used_at", "account_action_tokens", ["used_at"])
    op.create_index("ix_account_action_tokens_user_purpose", "account_action_tokens", ["user_id", "purpose", "used_at"])

    op.create_table(
        "auth_rate_limit_buckets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope", "key_hash", name="uq_auth_rate_limit_scope_key"),
    )
    op.create_index("ix_auth_rate_limit_window", "auth_rate_limit_buckets", ["window_started_at"])

    op.add_column("notification_jobs", sa.Column("delivery_body", sa.String(4096), nullable=True))
    op.add_column("notification_jobs", sa.Column("delivery_expires_at", sa.DateTime(timezone=True), nullable=True))

    for column in ("gstin", "pan", "bank_account_number", "bank_ifsc"):
        op.alter_column("hotel_verifications", column, existing_type=sa.String(length=50), type_=sa.String(length=1024), nullable=True)
    op.add_column("hotel_verifications", sa.Column("document_storage_key", sa.String(512), nullable=True))
    op.add_column("hotel_verifications", sa.Column("document_original_name", sa.String(255), nullable=True))
    op.add_column("hotel_verifications", sa.Column("document_content_type", sa.String(100), nullable=True))
    op.add_column("hotel_verifications", sa.Column("document_size", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, gstin, pan, bank_account_number, bank_ifsc FROM hotel_verifications")).mappings()
    for row in rows:
        bind.execute(sa.text("UPDATE hotel_verifications SET gstin=:gstin, pan=:pan, bank_account_number=:bank, bank_ifsc=:ifsc WHERE id=:id"), {
            "id": row["id"], "gstin": encrypt_sensitive(row["gstin"]), "pan": encrypt_sensitive(row["pan"]),
            "bank": encrypt_sensitive(row["bank_account_number"]), "ifsc": encrypt_sensitive(row["bank_ifsc"]),
        })


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, gstin, pan, bank_account_number, bank_ifsc FROM hotel_verifications")).mappings()
    for row in rows:
        bind.execute(sa.text("UPDATE hotel_verifications SET gstin=:gstin, pan=:pan, bank_account_number=:bank, bank_ifsc=:ifsc WHERE id=:id"), {
            "id": row["id"], "gstin": decrypt_sensitive(row["gstin"]), "pan": decrypt_sensitive(row["pan"]),
            "bank": decrypt_sensitive(row["bank_account_number"]), "ifsc": decrypt_sensitive(row["bank_ifsc"]),
        })
    for column in ("document_size", "document_content_type", "document_original_name", "document_storage_key"):
        op.drop_column("hotel_verifications", column)
    op.alter_column("hotel_verifications", "gstin", existing_type=sa.String(1024), type_=sa.String(15), nullable=True)
    op.alter_column("hotel_verifications", "pan", existing_type=sa.String(1024), type_=sa.String(10), nullable=True)
    op.alter_column("hotel_verifications", "bank_account_number", existing_type=sa.String(1024), type_=sa.String(50), nullable=True)
    op.alter_column("hotel_verifications", "bank_ifsc", existing_type=sa.String(1024), type_=sa.String(11), nullable=True)
    op.drop_column("notification_jobs", "delivery_expires_at")
    op.drop_column("notification_jobs", "delivery_body")
    op.drop_table("auth_rate_limit_buckets")
    op.drop_table("account_action_tokens")
    op.drop_table("auth_sessions")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "auth_version")
