from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260405_0010"
down_revision = "20260404_0009"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in set(inspect(op.get_bind()).get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_table("user_learning_profiles"):
        return

    additions: list[tuple[str, sa.Column]] = [
        ("skills", sa.Column("skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))),
        ("work_experience", sa.Column("work_experience", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))),
        ("education_history", sa.Column("education_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))),
        ("profile_display_name", sa.Column("profile_display_name", sa.String(length=255), nullable=False, server_default="")),
        ("profile_avatar_url", sa.Column("profile_avatar_url", sa.String(length=1024), nullable=False, server_default="")),
        ("profile_headline", sa.Column("profile_headline", sa.Text(), nullable=False, server_default="")),
        ("about_me", sa.Column("about_me", sa.Text(), nullable=False, server_default="")),
        ("contact_email", sa.Column("contact_email", sa.String(length=255), nullable=False, server_default="")),
        ("contact_phone", sa.Column("contact_phone", sa.String(length=128), nullable=False, server_default="")),
        ("contact_location", sa.Column("contact_location", sa.String(length=255), nullable=False, server_default="")),
        ("general_title", sa.Column("general_title", sa.String(length=255), nullable=False, server_default="")),
        ("date_of_birth", sa.Column("date_of_birth", sa.String(length=64), nullable=False, server_default="")),
        ("gender", sa.Column("gender", sa.String(length=64), nullable=False, server_default="")),
    ]

    for column_name, column in additions:
        if not _has_column("user_learning_profiles", column_name):
            op.add_column("user_learning_profiles", column)


def downgrade() -> None:
    if not _has_table("user_learning_profiles"):
        return

    for column_name in [
        "gender",
        "date_of_birth",
        "general_title",
        "contact_location",
        "contact_phone",
        "contact_email",
        "about_me",
        "profile_headline",
        "profile_avatar_url",
        "profile_display_name",
        "education_history",
        "work_experience",
        "skills",
    ]:
        if _has_column("user_learning_profiles", column_name):
            op.drop_column("user_learning_profiles", column_name)
