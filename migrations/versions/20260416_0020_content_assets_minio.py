from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260416_0020"
down_revision = "20260411_0019"
branch_labels = None
depends_on = None

TABLE_NAME = "content_assets"


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("asset_kind", sa.String(length=32), nullable=False, server_default="downloadable_file"),
        sa.Column("media_kind", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("bucket_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("storage_key", sa.String(length=1024), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("original_filename", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("normalized_filename", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("file_extension", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="seeded_course_asset"),
        sa.Column("scope_type", sa.String(length=32), nullable=False, server_default="course"),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("learning_path_id", sa.String(length=128), sa.ForeignKey("learning_paths.id", ondelete="SET NULL"), nullable=True),
        sa.Column("node_id", sa.String(length=128), nullable=True),
        sa.Column("chapter_id", sa.String(length=128), nullable=True),
        sa.Column("branch_id", sa.String(length=128), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attempt_id", sa.String(length=128), nullable=True),
        sa.Column("asset_status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("alt_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("download_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("file_category", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("poster_asset_id", sa.String(length=128), sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transcript_asset_id", sa.String(length=128), sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("thumbnail_asset_id", sa.String(length=128), sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_index("ix_content_assets_asset_kind", TABLE_NAME, ["asset_kind"], unique=False)
    op.create_index("ix_content_assets_media_kind", TABLE_NAME, ["media_kind"], unique=False)
    op.create_index("ix_content_assets_source_type", TABLE_NAME, ["source_type"], unique=False)
    op.create_index("ix_content_assets_scope_type", TABLE_NAME, ["scope_type"], unique=False)
    op.create_index("ix_content_assets_owner_user_id", TABLE_NAME, ["owner_user_id"], unique=False)
    op.create_index("ix_content_assets_uploaded_by_user_id", TABLE_NAME, ["uploaded_by_user_id"], unique=False)
    op.create_index("ix_content_assets_learning_path_id", TABLE_NAME, ["learning_path_id"], unique=False)
    op.create_index("ix_content_assets_node_id", TABLE_NAME, ["node_id"], unique=False)
    op.create_index("ix_content_assets_attempt_id", TABLE_NAME, ["attempt_id"], unique=False)
    op.create_index("ix_content_assets_asset_status", TABLE_NAME, ["asset_status"], unique=False)
    op.create_index("ix_content_assets_normalized_filename", TABLE_NAME, ["normalized_filename"], unique=False)
    op.create_index("ix_content_assets_checksum_sha256", TABLE_NAME, ["checksum_sha256"], unique=False)


def downgrade() -> None:
    if not _has_table(TABLE_NAME):
        return
    op.drop_index("ix_content_assets_checksum_sha256", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_normalized_filename", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_asset_status", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_attempt_id", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_node_id", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_learning_path_id", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_uploaded_by_user_id", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_owner_user_id", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_scope_type", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_source_type", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_media_kind", table_name=TABLE_NAME)
    op.drop_index("ix_content_assets_asset_kind", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
