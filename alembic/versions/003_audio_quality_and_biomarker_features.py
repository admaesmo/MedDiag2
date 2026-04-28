"""003 — add audio quality reports and biomarker feature store

Revision ID: 003
Revises: 002
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


NEW_AUDIO_STATUS_CHECK = (
    "status IN ("
    "'uploaded','preprocessing','processing','quality_checked','rejected',"
    "'features_extracted','partial_features','inference_completed',"
    "'processed','transcribed','failed','archived'"
    ")"
)

OLD_AUDIO_STATUS_CHECK = "status IN ('uploaded','processing','processed','transcribed','failed','archived')"


def upgrade() -> None:
    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.drop_constraint("ck_audio_status", type_="check")
        batch_op.create_check_constraint("ck_audio_status", NEW_AUDIO_STATUS_CHECK)

    op.create_table(
        "audio_quality_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "audio_record_id",
            sa.Integer(),
            sa.ForeignKey("audio_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("quality_status", sa.String(50), nullable=False, server_default="invalid"),
        sa.Column("noise_level", sa.Float(), nullable=True),
        sa.Column("clipping", sa.Float(), nullable=True),
        sa.Column("silence_ratio", sa.Float(), nullable=True),
        sa.Column("rms", sa.Float(), nullable=True),
        sa.Column("peak_amplitude", sa.Float(), nullable=True),
        sa.Column("stability_score", sa.Float(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quality_score >= 0 AND quality_score <= 1", name="ck_audio_quality_score_range"),
        sa.CheckConstraint("quality_status IN ('valid','low_quality','invalid')", name="ck_audio_quality_status"),
    )
    op.create_index(
        "ix_audio_quality_reports_audio_record_id",
        "audio_quality_reports",
        ["audio_record_id"],
    )

    op.create_table(
        "biomarker_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "audio_record_id",
            sa.Integer(),
            sa.ForeignKey("audio_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("extractor_version", sa.String(50), nullable=False),
        sa.Column("feature_schema_version", sa.String(50), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("feature_status", sa.String(50), nullable=False, server_default="complete"),
        sa.Column("ready_for_inference", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("missing_features_json", sa.JSON(), nullable=True),
        sa.Column("invalid_features_json", sa.JSON(), nullable=True),
        sa.Column("diagnosis_id", sa.Integer(), sa.ForeignKey("diagnoses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("feature_status IN ('complete','partial','failed')", name="ck_biomarker_feature_status"),
    )
    op.create_index(
        "ix_biomarker_features_audio_record_id",
        "biomarker_features",
        ["audio_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_biomarker_features_audio_record_id", table_name="biomarker_features")
    op.drop_table("biomarker_features")

    op.drop_index("ix_audio_quality_reports_audio_record_id", table_name="audio_quality_reports")
    op.drop_table("audio_quality_reports")

    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.drop_constraint("ck_audio_status", type_="check")
        batch_op.create_check_constraint("ck_audio_status", OLD_AUDIO_STATUS_CHECK)
