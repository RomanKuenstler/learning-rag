from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260404_0006"
down_revision = "20260401_0005"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_table("files"):
        return

    if not _has_column("files", "is_global"):
        op.add_column("files", sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))
    if not _has_column("files", "source_origin"):
        op.add_column("files", sa.Column("source_origin", sa.String(length=32), nullable=False, server_default="unknown"))

    op.execute(
        """
        UPDATE files
        SET is_global = CASE
            WHEN is_system = TRUE THEN TRUE
            WHEN uploaded_by_user_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM users
                WHERE users.id = files.uploaded_by_user_id
                AND users.role = 'admin'
            ) THEN TRUE
            ELSE FALSE
        END
        """
    )

    op.execute(
        """
        UPDATE files
        SET source_origin = CASE
            WHEN is_system = TRUE THEN 'system_data'
            WHEN uploaded_by_user_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM users
                WHERE users.id = files.uploaded_by_user_id
                AND users.role = 'admin'
            ) THEN 'admin_upload'
            WHEN uploaded_by_user_id IS NOT NULL THEN 'user_upload'
            ELSE 'unknown'
        END
        """
    )


def downgrade() -> None:
    if not _has_table("files"):
        return
    if _has_column("files", "source_origin"):
        with op.batch_alter_table("files") as batch_op:
            batch_op.drop_column("source_origin")
    if _has_column("files", "is_global"):
        with op.batch_alter_table("files") as batch_op:
            batch_op.drop_column("is_global")
