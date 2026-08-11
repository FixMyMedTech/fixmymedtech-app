import os
import re
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_API_SECRET_KEY")
supa_client: Client = create_client(url, key)

uri_db: str = os.environ.get("SUPABASE_DB_URI")

if uri_db and uri_db.startswith("postgresql://") and "+" not in uri_db.split("://")[0]:
    uri_db = uri_db.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(uri_db, echo=False, future=True, pool_size=5, max_overflow=3)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

Base = declarative_base()
meta = MetaData()
