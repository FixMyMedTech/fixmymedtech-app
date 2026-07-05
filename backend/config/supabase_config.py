import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker,Session
from sqlalchemy.ext.declarative import declarative_base
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
load_dotenv()

# Connect to supabase storage
url: str = os.environ.get("SUPABASE_URL")

# Set supabase client
key: str = os.environ.get("SUPABASE_API_SECRET_KEY")
supa_client: Client = create_client(url, key)

# Connect to supabase DB using sqlalchemy
uri_db: str = os.environ.get("SUPABASE_DB_URI")

engine = create_async_engine(uri_db, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

Base = declarative_base()
meta = MetaData()


# engine = create_engine(uri_db,
#                        pool_size=10,  # Adjust based on your needs
#                         max_overflow=5,  # Additional connections allowed beyond pool_size
#                         pool_timeout=30,  # Timeout for acquiring a connection
#                         pool_recycle=1800,  # Recycle connections after 30 minutes
#                     )  
# SessionLocal = sessionmaker(autocommit = False,autoflush = False, bind =engine)
# Base = declarative_base()
# # conn = engine.connect()
# meta = MetaData()

# def get_db():
#     try:
#         db=SessionLocal()
#         yield db
#     finally:
#         db.close()