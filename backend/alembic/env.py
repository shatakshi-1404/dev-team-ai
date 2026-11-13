from sqlalchemy import create_engine

from alembic import context
from app import models  # noqa: F401  (register tables)
from app.config import get_settings
from app.db import Base

target_metadata = Base.metadata


def run_migrations() -> None:
    url = get_settings().database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=url.startswith("sqlite")
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
