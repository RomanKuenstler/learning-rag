from __future__ import annotations

from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config

_migration_lock = Lock()
_migrated_urls: set[str] = set()


def run_migrations(database_url: str, *, force: bool = False) -> None:
    with _migration_lock:
        if not force and database_url in _migrated_urls:
            return
        root_dir = Path(__file__).resolve().parents[2]
        config = Config()
        config.set_main_option("script_location", str(root_dir / "migrations"))
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")
        _migrated_urls.add(database_url)
