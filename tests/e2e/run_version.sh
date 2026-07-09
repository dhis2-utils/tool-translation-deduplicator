#!/usr/bin/env bash
# Run the full per-version test cycle against a broker instance:
# wait for the API, install the app zip, seed duplicates, run the e2e suite.
#
# Usage: tests/e2e/run_version.sh <host> <label>
#   e.g. tests/e2e/run_version.sh dhis2-agent-td41 2.41-sl
# Assumes admin:district and the DB at <host>-db:5432 (broker defaults).
set -euo pipefail

HOST="$1"
LABEL="$2"
BASE="http://$HOST:8080"
ZIP=$(ls build/bundle/tool-translation-deduplicator-*.zip | head -1)
MANIFEST="${TMPDIR:-/tmp}/seed-manifest-$LABEL.json"

echo "== waiting for $BASE"
for i in $(seq 1 90); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -u admin:district --max-time 5 "$BASE/api/system/info" 2>/dev/null || true)
    [ "$code" = "200" ] && break
    sleep 10
done
[ "$code" = "200" ] || { echo "instance never came up"; exit 1; }
curl -s -u admin:district "$BASE/api/system/info" | python3 -c "import json,sys; print('version:', json.load(sys.stdin)['version'])"

echo "== installing app"
curl -s -u admin:district -X DELETE -o /dev/null "$BASE/api/apps/tool-translation-deduplicator" || true
code=$(curl -s -u admin:district -F "file=@$ZIP" -o /dev/null -w '%{http_code}' "$BASE/api/apps")
[ "$code" = "204" ] || { echo "app install failed: $code"; exit 1; }

echo "== seeding duplicates"
DHIS2_URL="$BASE" DHIS2_USER=admin DHIS2_PASS=district DHIS2_DB_HOST="$HOST-db" \
    python3 tests/seed_duplicates.py "$MANIFEST"

echo "== running e2e suite"
DHIS2_URL="$BASE" DHIS2_USER=admin DHIS2_PASS=district LABEL="$LABEL" \
    SEED_MANIFEST="$MANIFEST" python3 tests/e2e/test_dedup_app.py
