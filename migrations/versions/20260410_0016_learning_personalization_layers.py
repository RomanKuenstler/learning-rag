from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260410_0016"
down_revision = "20260410_0015"
branch_labels = None
depends_on = None


TABLE_NAME = "user_learning_personalization_layers"


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_engine_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("identity_context_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resolved_identity_context_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("goal_intent_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resolved_goal_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("declared_preferences_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resolved_declared_tutor_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("diagnosed_learning_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resolved_diagnostic_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("capability_mastery_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resolved_capability_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("live_adaptation_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resolved_live_adaptation_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_source_hashes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_to_group_trace_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("change_log_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("identity_context_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("goal_intent_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("declared_preferences_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diagnosed_learning_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capability_mastery_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_adaptation_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", name="uq_user_learning_personalization_layers_user"),
    )
    op.create_index("ix_user_learning_personalization_layers_user_id", TABLE_NAME, ["user_id"], unique=False)


def downgrade() -> None:
    if not _has_table(TABLE_NAME):
        return
    op.drop_index("ix_user_learning_personalization_layers_user_id", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
