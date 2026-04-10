from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260404_0007"
down_revision = "20260404_0006"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("learning_paths"):
        op.create_table(
            "learning_paths",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("scope", sa.String(length=16), nullable=False, server_default="user"),
            sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("subject", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("difficulty_level", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_learning_paths_owner_user_id", "learning_paths", ["owner_user_id"])

    if not _has_table("learning_modules"):
        op.create_table(
            "learning_modules",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("learning_path_id", sa.String(length=128), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("learning_objectives", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("learning_path_id", "order_index", name="uq_learning_modules_path_order"),
        )
        op.create_index("ix_learning_modules_learning_path_id", "learning_modules", ["learning_path_id"])

    if not _has_table("learning_lessons"):
        op.create_table(
            "learning_lessons",
            sa.Column("id", sa.String(length=128), primary_key=True),
            sa.Column("module_id", sa.String(length=128), sa.ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("objectives", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("teaching_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("module_id", "order_index", name="uq_learning_lessons_module_order"),
        )
        op.create_index("ix_learning_lessons_module_id", "learning_lessons", ["module_id"])

    if not _has_table("learning_path_allowed_files"):
        op.create_table(
            "learning_path_allowed_files",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("learning_path_id", sa.String(length=128), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
            sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("learning_path_id", "file_id", name="uq_learning_path_allowed_files"),
        )
        op.create_index("ix_learning_path_allowed_files_learning_path_id", "learning_path_allowed_files", ["learning_path_id"])
        op.create_index("ix_learning_path_allowed_files_file_id", "learning_path_allowed_files", ["file_id"])

    if not _has_table("learning_path_allowed_tags"):
        op.create_table(
            "learning_path_allowed_tags",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("learning_path_id", sa.String(length=128), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tag", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("learning_path_id", "tag", name="uq_learning_path_allowed_tags"),
        )
        op.create_index("ix_learning_path_allowed_tags_learning_path_id", "learning_path_allowed_tags", ["learning_path_id"])

    if _has_table("chats"):
        if not _has_column("chats", "chat_type"):
            op.add_column("chats", sa.Column("chat_type", sa.String(length=32), nullable=False, server_default="normal"))
        if not _has_column("chats", "learning_path_id"):
            op.add_column("chats", sa.Column("learning_path_id", sa.String(length=128), nullable=True))
            op.create_foreign_key(
                "fk_chats_learning_path_id",
                "chats",
                "learning_paths",
                ["learning_path_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "ix_chats_learning_path_id" not in _index_names("chats"):
            op.create_index("ix_chats_learning_path_id", "chats", ["learning_path_id"])


def downgrade() -> None:
    if _has_table("chats") and _has_column("chats", "learning_path_id"):
        with op.batch_alter_table("chats") as batch_op:
            batch_op.drop_column("learning_path_id")
    if _has_table("chats") and _has_column("chats", "chat_type"):
        with op.batch_alter_table("chats") as batch_op:
            batch_op.drop_column("chat_type")
    if _has_table("learning_path_allowed_tags"):
        op.drop_table("learning_path_allowed_tags")
    if _has_table("learning_path_allowed_files"):
        op.drop_table("learning_path_allowed_files")
    if _has_table("learning_lessons"):
        op.drop_table("learning_lessons")
    if _has_table("learning_modules"):
        op.drop_table("learning_modules")
    if _has_table("learning_paths"):
        op.drop_table("learning_paths")
