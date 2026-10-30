# Importing the app modules creates the SQLAlchemy engine, which needs a URL.
# The unit tests never connect, so any well-formed URL will do.
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
