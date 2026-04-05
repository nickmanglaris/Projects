from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables and run lightweight column migrations."""
    from app.models import transaction, card, price_history, prospect, statement, app_config, grading_submission  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_migrations()


async def _run_migrations():
    """Add new columns to existing tables if they don't exist (SQLite ALTER TABLE)."""
    import logging
    logger = logging.getLogger(__name__)

    migrations = [
        ("price_history", "psa10_price", "REAL"),
        ("price_history", "psa9_price", "REAL"),
        ("price_history", "psa8_price", "REAL"),
        ("grading_submissions", "psa10_estimate", "REAL"),
        ("grading_submissions", "psa9_estimate", "REAL"),
    ]

    async with engine.connect() as conn:
        for table, column, col_type in migrations:
            result = await conn.execute(
                __import__("sqlalchemy").text(f"PRAGMA table_info({table})")
            )
            existing_columns = [row[1] for row in result.fetchall()]
            if column not in existing_columns:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                    )
                )
                await conn.commit()
                logger.info(f"Migration: added {column} to {table}")
            else:
                logger.debug(f"Migration: {column} already exists in {table}")
