from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260410_0015"
down_revision = "20260408_0014"
branch_labels = None
depends_on = None


TABLE_NAME = "user_ksa_drill_attempts"


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = inspect(op.get_bind()).get_columns(table_name)
    return any(str(column.get("name")) == column_name for column in columns)


def upgrade() -> None:
    if not _has_table(TABLE_NAME):
        return

    if not _has_column(TABLE_NAME, "source_topic_input_text"):
        op.add_column(TABLE_NAME, sa.Column("source_topic_input_text", sa.Text(), nullable=False, server_default=""))
    if not _has_column(TABLE_NAME, "topic_classification_json"):
        op.add_column(TABLE_NAME, sa.Column("topic_classification_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if not _has_column(TABLE_NAME, "rounds_json"):
        op.add_column(TABLE_NAME, sa.Column("rounds_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    if not _has_table(TABLE_NAME):
        return

    if _has_column(TABLE_NAME, "rounds_json"):
        op.drop_column(TABLE_NAME, "rounds_json")
    if _has_column(TABLE_NAME, "topic_classification_json"):
        op.drop_column(TABLE_NAME, "topic_classification_json")
    if _has_column(TABLE_NAME, "source_topic_input_text"):
        op.drop_column(TABLE_NAME, "source_topic_input_text")
