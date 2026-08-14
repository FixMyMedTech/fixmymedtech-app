# ============================================================
# Migration runner — applies pending SQL migrations on startup.
#
# Migrations live in infrastructure/migrations/*.sql and are applied
# in filename order. Already-applied migrations are tracked in the
# fixmymedtech.schema_migrations table, so each file runs exactly once.
# ============================================================

import os
from pathlib import Path

from sqlalchemy import text

MIGRATIONS_DIR = os.environ.get("MIGRATIONS_DIR", "infrastructure/migrations")
TRACKING_TABLE = "fixmymedtech.schema_migrations"


async def _get_driver_conn(conn):
    """Return the raw asyncpg connection (supports multi-statement SQL)."""
    raw = await conn.get_raw_connection()
    return raw.driver_connection


async def run_migrations(engine) -> list:
    """Apply any pending migrations. Returns the list of applied filenames."""
    applied = []
    migrations_dir = Path(MIGRATIONS_DIR)
    if not migrations_dir.is_dir():
        print(f"[migrations] directory not found: {migrations_dir} — skipping")
        return applied

    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print("[migrations] no migration files found")
        return applied

    async with engine.connect() as conn:
        # Ensure the tracking table exists
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS fixmymedtech"))
        await conn.execute(text(
            f"""
            CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
                name       TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        ))
        await conn.commit()

        driver = await _get_driver_conn(conn)

        for f in files:
            already = (await conn.execute(
                text(f"SELECT 1 FROM {TRACKING_TABLE} WHERE name = :n"),
                {"n": f.name},
            )).scalar()
            if already:
                print(f"[migrations] {f.name} — already applied, skipping")
                continue

            sql = f.read_text()
            await driver.execute(sql)
            await conn.execute(
                text(f"INSERT INTO {TRACKING_TABLE} (name) VALUES (:n)"),
                {"n": f.name},
            )
            await conn.commit()
            applied.append(f.name)
            print(f"[migrations] applied {f.name}")

    return applied
