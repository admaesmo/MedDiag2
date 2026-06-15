"""007 — add audio_record_id to diagnoses

Revision ID: 007
Revises: 006
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("diagnoses") as batch_op:
        batch_op.add_column(sa.Column("audio_record_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_diagnoses_audio_record",
            "audio_records",
            ["audio_record_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("diagnoses") as batch_op:
        batch_op.drop_constraint("fk_diagnoses_audio_record", type_="foreignkey")
        batch_op.drop_column("audio_record_id")
