from alembic import context
from sqlalchemy import create_engine

from optimizer.config import Settings
from optimizer.persistence import metadata

engine = create_engine(Settings().app_dsn.get_secret_value())
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
