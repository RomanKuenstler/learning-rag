from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260408_0013"
down_revision = "20260408_0012"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _has_table("user_ksa_drill_attempts"):
        op.create_table(
            "user_ksa_drill_attempts",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("assessment_version", sa.String(length=32), nullable=False, server_default="ksa-drill-v1"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
            sa.Column("selected_topic_keys_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("question_set_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("answers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_user_ksa_drill_attempts_user_id", "user_ksa_drill_attempts", ["user_id"])


def downgrade() -> None:
    if _has_table("user_ksa_drill_attempts"):
        op.drop_table("user_ksa_drill_attempts")
