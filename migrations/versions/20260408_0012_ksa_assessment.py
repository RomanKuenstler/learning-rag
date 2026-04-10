from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260408_0012"
down_revision = "20260405_0011"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _has_table("user_ksa_profiles"):
        op.create_table(
            "user_ksa_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("has_assessment", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("assessment_version", sa.String(length=32), nullable=False, server_default="ksa-v1"),
            sa.Column("profile_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("user_id", name="uq_user_ksa_profiles_user"),
        )
        op.create_index("ix_user_ksa_profiles_user_id", "user_ksa_profiles", ["user_id"])

    if not _has_table("user_ksa_assessment_attempts"):
        op.create_table(
            "user_ksa_assessment_attempts",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("assessment_version", sa.String(length=32), nullable=False, server_default="ksa-v1"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
            sa.Column("answers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_user_ksa_assessment_attempts_user_id", "user_ksa_assessment_attempts", ["user_id"])


def downgrade() -> None:
    if _has_table("user_ksa_assessment_attempts"):
        op.drop_table("user_ksa_assessment_attempts")
    if _has_table("user_ksa_profiles"):
        op.drop_table("user_ksa_profiles")
