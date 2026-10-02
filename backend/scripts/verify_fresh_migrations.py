"""Apply the complete Alembic chain to a disposable MySQL database."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings


def main() -> int:
    source_url = make_url(settings.DATABASE_URL)
    if source_url.get_backend_name() != "mysql":
        raise RuntimeError("Fresh migration verification requires the supported MySQL database")

    database_name = f"travel_platform_migration_check_{secrets.token_hex(5)}"
    server_engine = create_engine(source_url.set(database=None), pool_pre_ping=True)
    try:
        with server_engine.begin() as connection:
            connection.execute(text(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))

        environment = os.environ.copy()
        environment["DATABASE_URL"] = source_url.set(database=database_name).render_as_string(hide_password=False)
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=environment,
            check=False,
        )
        if completed.returncode:
            return completed.returncode
        print(f"Fresh migration verification passed at head for disposable database {database_name}")
        return 0
    finally:
        with server_engine.begin() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS `{database_name}`"))
        server_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
