"""004 — create audio_quality_reports + update status constraint

Revision ID: 004
Revises: 003
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1. Drop old CheckConstraint on audio_records ---
    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.drop_constraint("ck_audio_status", type_="check")

    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.create_check_constraint(
            "ck_audio_status",
            "status IN ('uploaded','processing','quality_checked','rejected',"
            "'partial_features','processed','transcribed','failed','archived')",
        )

    # --- 2. Create audio_quality_reports ---
    op.create_table(
        "audio_quality_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "audio_record_id",
            sa.Integer(),
            sa.ForeignKey("audio_records.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # Verdict
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),

        # Signal metrics
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("rms_energy", sa.Float(), nullable=True),
        sa.Column("peak_amplitude", sa.Float(), nullable=True),
        sa.Column("clipping_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("clipping_ratio", sa.Float(), nullable=True),
        sa.Column("snr_db", sa.Float(), nullable=True),
        sa.Column("silence_ratio", sa.Float(), nullable=True),
        sa.Column("noise_floor_db", sa.Float(), nullable=True),
        sa.Column("bandwidth_hz", sa.Float(), nullable=True),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("audio_quality_reports")

    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.drop_constraint("ck_audio_status", type_="check")

    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.create_check_constraint(
            "ck_audio_status",
            "status IN ('uploaded','processing','processed','transcribed','failed','archived')",
        )
