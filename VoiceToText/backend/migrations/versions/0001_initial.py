"""Initial preferences and transcriptions.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("user_preferences", sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("default_language", sa.String(32), nullable=False), sa.Column("default_tone", sa.String(32), nullable=False), sa.Column("auto_detect_language", sa.Boolean(), nullable=False), sa.Column("save_audio", sa.Boolean(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("transcriptions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("raw_text", sa.Text(), nullable=False), sa.Column("processed_text", sa.Text()), sa.Column("language", sa.String(32), nullable=False), sa.Column("tone", sa.String(32), nullable=False), sa.Column("stt_model", sa.String(128), nullable=False), sa.Column("llm_model", sa.String(128)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_transcriptions_user_id", "transcriptions", ["user_id"])


def downgrade():
    op.drop_index("ix_transcriptions_user_id", "transcriptions")
    op.drop_table("transcriptions")
    op.drop_table("user_preferences")
