import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
from sqlalchemy import engine_from_config, pool
from alembic import context
from logging.config import fileConfig
from app.database import Base, engine

# Alembic Config
config = context.config



# Logging Setup
fileConfig(config.config_file_name)

# Ensure database URL is set
database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:root@localhost:5432/postgres')
config.set_main_option('sqlalchemy.url', database_url)

from app.database import Base, engine  # Ensure this import works

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
