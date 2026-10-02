import sys
from os.path import abspath, dirname
from logging.config import fileConfig


from sqlalchemy import pool

from alembic import context

# Add backend directory to sys.path to allow importing from app
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.core.config import settings
from app.models.base import Base
from app import models  # noqa: F401 - registers all model metadata for autogenerate
from app.database import engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set up target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to associate a connection
    with the context, using the application's engine.
    """
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
