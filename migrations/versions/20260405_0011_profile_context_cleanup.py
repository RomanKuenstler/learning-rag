from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "20260405_0011"
down_revision = "20260405_0010"
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

    for column_name in [
        "profile_avatar_url",
        "profile_headline",
        "contact_email",
        "contact_phone",
        "gender",
        "professional_context",
        "education_background",
    ]:
        if _has_column("user_learning_profiles", column_name):
            op.drop_column("user_learning_profiles", column_name)


def downgrade() -> None:
    # intentionally no-op for removed columns in this branch
    pass
