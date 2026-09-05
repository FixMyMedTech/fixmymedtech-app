"""Database engine + async session factory.

Connects directly to PostgreSQL (Supabase-hosted pooler or local) via
SQLAlchemy. No Supabase REST/API layer is used.
"""

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DB_SCHEMA = os.getenv("DB_SCHEMA", "fixmymedtech")

uri_db: str = os.environ.get("DATABASE_URL", "")

if uri_db and uri_db.startswith("postgresql://") and "+" not in uri_db.split("://")[0]:
    uri_db = uri_db.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(uri_db, echo=False, future=True, pool_size=5, max_overflow=3)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session