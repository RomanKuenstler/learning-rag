from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260404_0009"
down_revision = "20260404_0008"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _has_table("diagnostic_definitions"):
        op.create_table(
            "diagnostic_definitions",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("diagnostic_type", sa.String(length=16), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("diagnostic_type", name="uq_diagnostic_definitions_type"),
        )

    if not _has_table("diagnostic_versions"):
        op.create_table(
            "diagnostic_versions",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("definition_id", sa.String(length=128), sa.ForeignKey("diagnostic_definitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("source_document_name", sa.String(length=512), nullable=False),
            sa.Column("source_document_hash", sa.String(length=64), nullable=False),
            sa.Column("content_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("definition_id", "version", name="uq_diagnostic_versions_definition_version"),
        )
        op.create_index("ix_diagnostic_versions_definition_id", "diagnostic_versions", ["definition_id"])

    if not _has_table("diagnostic_questions"):
        op.create_table(
            "diagnostic_questions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("version_id", sa.String(length=128), sa.ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("question_key", sa.String(length=128), nullable=False),
            sa.Column("section_key", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("question_type", sa.String(length=32), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("scoring_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("version_id", "question_key", name="uq_diagnostic_questions_version_question_key"),
        )
        op.create_index("ix_diagnostic_questions_version_id", "diagnostic_questions", ["version_id"])

    if not _has_table("diagnostic_options"):
        op.create_table(
            "diagnostic_options",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("question_id", sa.Integer(), sa.ForeignKey("diagnostic_questions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("option_key", sa.String(length=128), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("label", sa.Text(), nullable=False),
            sa.Column("value_text", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("scoring_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("question_id", "option_key", name="uq_diagnostic_options_question_option_key"),
        )
        op.create_index("ix_diagnostic_options_question_id", "diagnostic_options", ["question_id"])

    if not _has_table("diagnostic_scoring_rules"):
        op.create_table(
            "diagnostic_scoring_rules",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("version_id", sa.String(length=128), sa.ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rule_key", sa.String(length=128), nullable=False),
            sa.Column("rule_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_diagnostic_scoring_rules_version_id", "diagnostic_scoring_rules", ["version_id"])

    if not _has_table("user_diagnostic_attempts"):
        op.create_table(
            "user_diagnostic_attempts",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("definition_versions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
            sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_user_diagnostic_attempts_user_id", "user_diagnostic_attempts", ["user_id"])

    if not _has_table("user_diagnostic_answers"):
        op.create_table(
            "user_diagnostic_answers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("attempt_id", sa.String(length=128), sa.ForeignKey("user_diagnostic_attempts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("diagnostic_type", sa.String(length=16), nullable=False),
            sa.Column("question_key", sa.String(length=128), nullable=False),
            sa.Column("answer_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("attempt_id", "diagnostic_type", "question_key", name="uq_user_diagnostic_answer"),
        )
        op.create_index("ix_user_diagnostic_answers_attempt_id", "user_diagnostic_answers", ["attempt_id"])

    if not _has_table("user_diagnostic_results"):
        op.create_table(
            "user_diagnostic_results",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("attempt_id", sa.String(length=128), sa.ForeignKey("user_diagnostic_attempts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("attempt_id", name="uq_user_diagnostic_results_attempt"),
        )
        op.create_index("ix_user_diagnostic_results_attempt_id", "user_diagnostic_results", ["attempt_id"])

    if not _has_table("learning_state_checks"):
        op.create_table(
            "learning_state_checks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chat_id", sa.String(length=128), sa.ForeignKey("chats.id", ondelete="SET NULL"), nullable=True),
            sa.Column("mood", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("perceived_difficulty", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("needs_pause_or_input", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("preferred_format", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_learning_state_checks_user_id", "learning_state_checks", ["user_id"])
        op.create_index("ix_learning_state_checks_chat_id", "learning_state_checks", ["chat_id"])

    if not _has_table("explanation_feedback"):
        op.create_table(
            "explanation_feedback",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("feedback_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("re_explain_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_explanation_feedback_user_id", "explanation_feedback", ["user_id"])
        op.create_index("ix_explanation_feedback_message_id", "explanation_feedback", ["message_id"])


def downgrade() -> None:
    if _has_table("explanation_feedback"):
        op.drop_table("explanation_feedback")
    if _has_table("learning_state_checks"):
        op.drop_table("learning_state_checks")
    if _has_table("user_diagnostic_results"):
        op.drop_table("user_diagnostic_results")
    if _has_table("user_diagnostic_answers"):
        op.drop_table("user_diagnostic_answers")
    if _has_table("user_diagnostic_attempts"):
        op.drop_table("user_diagnostic_attempts")
    if _has_table("diagnostic_scoring_rules"):
        op.drop_table("diagnostic_scoring_rules")
    if _has_table("diagnostic_options"):
        op.drop_table("diagnostic_options")
    if _has_table("diagnostic_questions"):
        op.drop_table("diagnostic_questions")
    if _has_table("diagnostic_versions"):
        op.drop_table("diagnostic_versions")
    if _has_table("diagnostic_definitions"):
        op.drop_table("diagnostic_definitions")
