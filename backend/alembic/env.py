"""Alembic environment.

The database URL comes from app.core.config.settings, the same source
app/infrastructure/database/connection.py uses, so migrations and the running
app always target the same database. A caller may still override it with
`alembic -x sqlalchemy.url=...` or Config.set_main_option (used by the tests).
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

from app.core.config import settings
from app.infrastructure.database.connection import Base

# Imported for their side effect: each module registers a table on Base.metadata,
# which is what --autogenerate compares the database against.
from app.domain.entities.agent_trace import AgentTrace  # noqa: F401
from app.domain.entities.comment import Comment  # noqa: F401
from app.domain.entities.ticket import Ticket  # noqa: F401

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers stays off so running a migration in-process (tests,
    # a startup hook) does not silence the application's own loggers.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it against a database."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        # SQLite cannot ALTER most things in place; batch mode rewrites the table.
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
