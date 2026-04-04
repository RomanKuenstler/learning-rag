from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260404_0008"
down_revision = "20260404_0007"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _has_table("user_learning_preferences"):
        op.create_table(
            "user_learning_preferences",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("preferred_pace", sa.String(length=32), nullable=False, server_default="balanced"),
            sa.Column("explanation_depth", sa.String(length=32), nullable=False, server_default="balanced"),
            sa.Column("examples_vs_theory", sa.String(length=32), nullable=False, server_default="balanced"),
            sa.Column("structure_preference", sa.String(length=32), nullable=False, server_default="balanced"),
            sa.Column("checkpoint_frequency", sa.String(length=32), nullable=False, server_default="medium"),
            sa.Column("encouragement_level", sa.String(length=32), nullable=False, server_default="balanced"),
            sa.Column("guidance_level", sa.String(length=32), nullable=False, server_default="balanced"),
            sa.Column("recap_frequency", sa.String(length=32), nullable=False, server_default="medium"),
            sa.Column("preferred_learning_format", sa.String(length=32), nullable=False, server_default="mixed"),
            sa.Column("custom_preference_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", name="uq_user_learning_preferences_user"),
        )
        op.create_index("ix_user_learning_preferences_user_id", "user_learning_preferences", ["user_id"])

    if not _has_table("user_learning_profiles"):
        op.create_table(
            "user_learning_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("education_background", sa.Text(), nullable=False, server_default=""),
            sa.Column("current_skill_areas", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("interests", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("professional_context", sa.Text(), nullable=False, server_default=""),
            sa.Column("current_reason_for_learning", sa.Text(), nullable=False, server_default=""),
            sa.Column("preferred_form_of_address", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("learning_context_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", name="uq_user_learning_profiles_user"),
        )
        op.create_index("ix_user_learning_profiles_user_id", "user_learning_profiles", ["user_id"])

    if not _has_table("user_learning_goals"):
        op.create_table(
            "user_learning_goals",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_topic", sa.String(length=255), nullable=False),
            sa.Column("reason_for_learning", sa.Text(), nullable=False, server_default=""),
            sa.Column("target_level", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("deadline", sa.Date(), nullable=True),
            sa.Column("priority", sa.String(length=32), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_user_learning_goals_user_id", "user_learning_goals", ["user_id"])


def downgrade() -> None:
    if _has_table("user_learning_goals"):
        op.drop_table("user_learning_goals")
    if _has_table("user_learning_profiles"):
        op.drop_table("user_learning_profiles")
    if _has_table("user_learning_preferences"):
        op.drop_table("user_learning_preferences")
