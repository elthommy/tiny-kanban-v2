from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from tiny_kanban.config import get_settings
from tiny_kanban.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# When invoked programmatically (app startup, tests) the URL is set on the
# Alembic Config; when run from the CLI, fall back to app Settings so the
# DB path has a single source of truth.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # render_as_batch: SQLite can't ALTER most things in place; batch mode
        # makes future column changes work via table rebuild
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
