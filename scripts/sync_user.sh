#!/usr/bin/env bash
# After signing up via Supabase Auth, this script retrieves the user from
# Supabase Auth and inserts them into the local PostgreSQL for the FK to work.
#
# Usage: ./scripts/sync_user.sh <email>
# Prerequisites: SUPABASE_API_SERVICE_KEY in .env, local DB running

set -euo pipefail

EMAIL="${1:-}"
if [ -z "$EMAIL" ]; then
  echo "Usage: $0 <email>"
  exit 1
fi

source .env 2>/dev/null || true

echo "=== Syncing user $EMAIL to local DB ==="

# Get user from Supabase Auth via the admin API
USER_JSON=$(curl -s -X GET \
  "https://${SUPABASE_URL}/auth/v1/admin/users" \
  -H "apikey: ${SUPABASE_API_ANON_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_API_SECRET_KEY}" 2>/dev/null || echo "")

if [ -z "$USER_JSON" ]; then
  echo "⚠  Could not fetch users. Make sure SUPABASE_URL and keys are set in .env"
  echo "  You can manually insert the user:"
  echo "    docker compose exec db psql -U postgres -d fixmymedtech"
  echo "    INSERT INTO auth.users (id, email) VALUES ('<uuid-from-supabase>', '${EMAIL}');"
  exit 1
fi

# Extract user ID (rough parse — jq would be better)
USER_ID=$(echo "$USER_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for u in data.get('users', []):
    if u.get('email') == '$EMAIL':
        print(u['id'])
" 2>/dev/null || echo "")

if [ -z "$USER_ID" ]; then
  echo "User $EMAIL not found in Supabase. Create the account first at http://localhost:5173/signup"
  exit 1
fi

# Insert into local DB
docker compose exec -T db psql -U postgres -d fixmymedtech -c \
  "INSERT INTO auth.users (id, email) VALUES ('$USER_ID', '$EMAIL') ON CONFLICT (id) DO NOTHING;"

echo "✓ User $EMAIL synced (ID: $USER_ID)"
echo "  Now insert the profile:"
echo "  docker compose exec db psql -U postgres -d fixmymedtech -c \"INSERT INTO fixmymedtech.profiles (id, organization_id, full_name, role) VALUES ('$USER_ID', '00000000-0000-0000-0000-000000000001', 'Admin User', 'admin');\""
