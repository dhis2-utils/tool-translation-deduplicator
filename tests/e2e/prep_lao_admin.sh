#!/usr/bin/env bash
# The lao_hmis_demo seed ships with the admin account disabled.
# Wait for DHIS2 to answer (unauthenticated), re-enable admin at DB level,
# then restart Tomcat (DHIS2 caches failed logins until restart).
# Usage: tests/e2e/prep_lao_admin.sh <instance-name>   e.g. agent-tdlao42
# The target is a disposable broker container on a local Docker network
# that only serves plain HTTP; there is no TLS endpoint to point this at.
set -euo pipefail
NAME="$1"
HOST="dhis2-$NAME"
B="$DHIS2_BROKER_URL"; H="Authorization: Bearer $DHIS2_BROKER_TOKEN"

echo "== waiting for DHIS2 on $HOST (unauthenticated probe)"
for _ in $(seq 1 120); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://$HOST:8080/api/loginConfig" 2>/dev/null || true)
    case "$code" in 200|302|401) break;; *) ;; esac
    sleep 15
done
echo "probe code: $code"

echo "== enabling admin in DB"
python3 - "$HOST-db" <<'EOF'
import sys, bcrypt, pg8000.native
h = bcrypt.hashpw(b'district', bcrypt.gensalt(10)).decode()
con = pg8000.native.Connection('dhis', host=sys.argv[1], database='dhis2', password='dhis')
print('updated:', con.run("UPDATE userinfo SET disabled=false, password=:h WHERE username='admin' RETURNING uid", h=h))
con.close()
EOF

echo "== restarting tomcat"
curl -s -X POST -H "$H" "$B/instances/$NAME/stop" >/dev/null
sleep 10
curl -s -X POST -H "$H" "$B/instances/$NAME/start" >/dev/null
echo "done — run_version.sh will wait for authenticated API"
