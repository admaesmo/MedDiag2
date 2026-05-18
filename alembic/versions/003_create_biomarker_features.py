"""003 — create biomarker_features table

Revision ID: 003
Revises: 002
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "biomarker_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "audio_record_id",
            sa.Integer(),
            sa.ForeignKey("audio_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("extractor_version", sa.String(100), nullable=False),
        sa.Column("feature_schema_version", sa.String(100), nullable=False),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column("missing_features_json", sa.Text(), nullable=True),
        sa.Column("is_partial", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "audio_record_id",
            "extractor_version",
            "feature_schema_version",
            name="uq_audio_feature_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("biomarker_features")
