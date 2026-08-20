import re
import random
import string
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


def _slugify_name(full_name: str) -> str:
    """Convert 'Jane Smith' → 'jane.smith'."""
    slug = (full_name or "user").lower()
    slug = re.sub(r"[^a-z0-9]+", ".", slug)
    slug = slug.strip(".")
    slug = re.sub(r"\.{2,}", ".", slug)
    return slug or "user"


async def generate_username(full_name: str, db: AsyncSession) -> str:
    """Generate a unique username: 'jane.smith' + random 4 digits."""
    base = _slugify_name(full_name)
    for _ in range(20):
        suffix = "".join(random.choices(string.digits, k=4))
        candidate = f"{base}{suffix}"
        exists = await db.execute(
            select(text("1")).where(text("username = :u")).bindparams(u=candidate)
        )
        if not exists.scalar():
            return candidate
    raise RuntimeError("Could not generate a unique username")
