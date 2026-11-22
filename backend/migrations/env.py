from logging.config import fileConfig

from alembic import context

from app.core.database import engine
from app.models.domain import DomainBase
import app.models.domain  # noqa: F401 — registers every domain table in metadata


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = DomainBase.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
