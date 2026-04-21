"""002 — create audio_records table

Revision ID: 002
Revises: 001
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audio_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uuid", sa.String(36), unique=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),

        sa.Column("source_type", sa.String(50), server_default="upload"),
        sa.Column("original_filename", sa.Text()),
        sa.Column("stored_filename", sa.Text(), nullable=False),
        sa.Column("storage_provider", sa.String(50), nullable=False, server_default="local"),
        sa.Column("storage_path", sa.Text(), nullable=False),

        sa.Column("mime_type", sa.String(100)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("duration_seconds", sa.Float(), nullable=True),

        sa.Column("language_code", sa.String(10), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),

        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        sa.CheckConstraint(
            "status IN ('uploaded','processing','processed','transcribed','failed','archived')",
            name="ck_audio_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("audio_records")
