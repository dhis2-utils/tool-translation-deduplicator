#!/usr/bin/env bash
# e2e contract entry point (reference-tool-conventions TESTING.md, contract v1).
#
#   DHIS2_URL=http://localhost:8080 DHIS2_USER=<user> DHIS2_PASS=<password> \
#   APP_ZIP=$PWD/build/bundle/tool-translation-deduplicator-1.0.0.zip \
#   RESULTS_DIR=/tmp/e2e-results e2e/run.sh
#
# WARNING: changes and deletes data. Throwaway instances only.
# Exit codes: 0 all passed, 1 a test failed, 2 the suite could not run.
set -uo pipefail

missing=()
for var in DHIS2_URL DHIS2_USER DHIS2_PASS APP_ZIP RESULTS_DIR; do
    [[ -n "${!var:-}" ]] || missing+=("$var")
done
if (( ${#missing[@]} )); then
    echo "missing required environment variables: ${missing[*]}" >&2
    exit 2
fi
[[ -f "$APP_ZIP" ]] || { echo "APP_ZIP is not a file: $APP_ZIP" >&2; exit 2; }
[[ -d "$RESULTS_DIR" ]] || { echo "RESULTS_DIR is not a directory: $RESULTS_DIR" >&2; exit 2; }
python3 -c "import playwright" 2>/dev/null || {
    echo "Playwright for Python is missing: pip install -r e2e/requirements.txt" >&2
    exit 2
}

python3 "$(dirname "$0")/test_dedup_app.py" 2>&1 | tee "$RESULTS_DIR/run.log"
exit "${PIPESTATUS[0]}"
