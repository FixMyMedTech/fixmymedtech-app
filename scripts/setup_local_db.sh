#!/usr/bin/env bash
set -euo pipefail

echo "=== FixMyMedTech — Local DB Setup ==="

COMPOSE="docker compose -f docker-compose.local.yml"

# Start PostgreSQL
echo "[1/4] Starting PostgreSQL via Docker..."
$COMPOSE up -d db
echo " Waiting for PostgreSQL to be healthy..."
until $COMPOSE exec db pg_isready -U postgres -d fixmymedtech > /dev/null 2>&1; do
  sleep 1
done
echo " PostgreSQL is ready."

# Schema is auto-applied by the init.sql volume mount, but re-run to be safe
echo "[2/4] Applying schema..."
$COMPOSE exec -T db psql -U postgres -d fixmymedtech < ./db/init.sql
echo " Schema applied."

# Users now live in the local DB. Seed test data directly:
echo "[3/4] Seed test users (optional):"
echo "  - Run:  python scripts/seed_test_data.py"
echo ""

# .env check
if [ ! -f .env ]; then
  echo "[4/4] Creating .env from .env.example..."
  echo "  The local stack works with a fresh .env (SMTP/OAuth optional)."
else
  echo "[4/4] .env already exists, skipping."
fi

echo ""
echo "=== Done! Run: docker compose -f docker-compose.local.yml up --build -d ==="
