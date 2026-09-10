"""
Alembic env.py for ORCA Auth.

Reads DATABASE_URL from the environment so credentials are never hard-coded.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so "backend.*" imports resolve.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env FIRST — before any backend.auth module reads os.getenv()
import backend.auth._env  # noqa: F401, E402

# Import the ORM models so Alembic can compare against them.
from backend.auth.database import Base  # noqa: E402
import backend.auth.models  # noqa: E402, F401 — side-effect: registers User model

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Inject DATABASE_URL from the environment, overriding the (empty) ini value.
database_url = os.getenv("DATABASE_URL", "")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it in .env or your shell before running alembic."
    )
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Run migrations
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
