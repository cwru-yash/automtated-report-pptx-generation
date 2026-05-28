import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

logger = logging.getLogger(__name__)

LOCAL_DB_PATH = Path("artifacts") / "app.db"
LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if settings.DATABASE_URL.startswith("sqlite:///"):
    DB_URL = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
else:
    DB_URL = settings.DATABASE_URL or f"sqlite+aiosqlite:///{LOCAL_DB_PATH}"

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def init_db():
    # Import model modules before metadata creation so SQLAlchemy sees tables.
    import app.deck.models  # noqa: F401
    import app.queue.postgres_queue  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
