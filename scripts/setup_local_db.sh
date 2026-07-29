#!/usr/bin/env bash
set -euo pipefail

echo "=== FixMyMedTech — Local DB Setup ==="

# Start PostgreSQL
echo "[1/4] Starting PostgreSQL via Docker..."
docker compose up -d db
echo " Waiting for PostgreSQL to be healthy..."
until docker compose exec db pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done
echo " PostgreSQL is ready."

# Schema is auto-applied by the init.sql volume mount, but re-run to be safe
echo "[2/4] Applying schema..."
docker compose exec -T db psql -U postgres -d fixmymedtech < ./db/init.sql
echo " Schema applied."

# Prompt user to create a Supabase Auth account
echo ""
echo "[3/4] Create a Supabase Auth account for the demo:"
echo "  - Go to http://localhost:5173/signup"
echo "  - Register a new account"
echo "  - Then run:  ./scripts/sync_user.sh <your-email>"
echo ""
echo "  Or use the setup script with an existing Firebase user."

# .env check
if [ ! -f .env ]; then
  echo "[4/4] Creating .env from .env.local.example..."
  echo "⚠  Edit .env with your Supabase credentials first!"
else
  echo "[4/4] .env already exists, skipping."
fi

echo ""
echo "=== Done! Run: docker compose up ==="
