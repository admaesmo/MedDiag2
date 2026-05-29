"""005 — create voice_sessions and extend audio_records

Revision ID: 005
Revises: 004
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    existing_cols = [c["name"] for c in inspector.get_columns("audio_records")]

    # 1. Crear voice_sessions solo si no existe (primera ejecución puede haber
    #    creado la tabla antes de fallar en el constraint FK)
    if "voice_sessions" not in existing_tables:
        op.create_table(
            "voice_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("uuid", sa.String(36), nullable=False, unique=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("max_takes", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("status", sa.String(50), nullable=False, server_default="collecting"),
            sa.Column("aggregated_features_json", sa.Text(), nullable=True),
            sa.Column("variance_json", sa.Text(), nullable=True),
            sa.Column("valid_takes_count", sa.Integer(), nullable=True),
            sa.Column("session_confidence", sa.Float(), nullable=True),
            sa.Column(
                "diagnosis_id",
                sa.Integer(),
                sa.ForeignKey("diagnoses.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "status IN ('collecting','ready','processing','completed','failed','cancelled')",
                name="ck_session_status",
            ),
            sa.CheckConstraint(
                "max_takes BETWEEN 2 AND 5",
                name="ck_session_max_takes",
            ),
        )

    # 2. Agregar columnas faltantes en audio_records (batch mode para SQLite)
    missing_cols = [
        col for col in ("session_id", "take_number")
        if col not in existing_cols
    ]
    if missing_cols:
        with op.batch_alter_table("audio_records") as batch_op:
            if "session_id" in missing_cols:
                batch_op.add_column(sa.Column("session_id", sa.Integer(), nullable=True))
            if "take_number" in missing_cols:
                batch_op.add_column(sa.Column("take_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    # Invertir en orden opuesto
    with op.batch_alter_table("audio_records") as batch_op:
        batch_op.drop_column("take_number")
        batch_op.drop_column("session_id")

    op.drop_table("voice_sessions")
