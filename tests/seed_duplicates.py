#!/usr/bin/env python3
"""Seed duplicate translations into a DHIS2 instance for testing the
Translation Deduplicator app.

Only run against disposable test instances!

Since DHIS2 2.40 the metadata API *rejects* duplicate translations
(error E1106) — duplicates only exist as legacy data. So this script
writes the duplicates directly to the database (translations jsonb
column), then clears the server cache and verifies through the API
that the duplicates are visible.

Usage:
    DHIS2_URL=http://dhis2-agent-td40:8080 DHIS2_USER=admin DHIS2_PASS=district \
    DHIS2_DB_HOST=dhis2-agent-td40-db \
        python3 tests/seed_duplicates.py [manifest-out.json]

Requires: pip install pg8000
"""

import base64
import json
import os
import sys
import urllib.request

import pg8000.native

BASE = os.environ.get("DHIS2_URL", "http://localhost:8080").rstrip("/")
USER = os.environ.get("DHIS2_USER", "admin")
PASS = os.environ.get("DHIS2_PASS", "district")
DB_HOST = os.environ["DHIS2_DB_HOST"]
DB_PORT = int(os.environ.get("DHIS2_DB_PORT", "5432"))
DB_NAME = os.environ.get("DHIS2_DB_NAME", "dhis2")
DB_USER = os.environ.get("DHIS2_DB_USER", "dhis")
DB_PASS = os.environ.get("DHIS2_DB_PASS", "dhis")

AUTH = "Basic " + base64.b64encode(f"{USER}:{PASS}".encode()).decode()


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{BASE}/api/{path}",
        method=method,
        headers={"Authorization": AUTH, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


# (collection, table, how many objects, duplicate specs, fixable-via-API)
# Each spec: (locale, property, [values...]).
SEED_PLAN = [
    # NOTE: fully identical duplicate records (same locale+property+value)
    # are collapsed by the API on read (Set semantics server-side), so
    # they can never reach this app — seed only differing values.
    ("dataElements", "dataelement", 2, [
        ("fr", "NAME", ["Doublon A", "Doublon B"]),
        ("fr", "SHORT_NAME", ["Abrégé A", "Abrégé B"]),
    ], True),
    ("indicators", "indicator", 1, [
        ("fr", "NAME", ["Indicateur X", "Indicateur Y"]),
    ], True),
    ("organisationUnits", "organisationunit", 1, [
        ("fr", "NAME", ["Unité 1", "Unité 2"]),
    ], True),
    # The server silently ignores categoryOptionCombo updates — the app
    # must flag these as not fixable via the API.
    ("categoryOptionCombos", "categoryoptioncombo", 1, [
        ("fr", "NAME", ["Combo A", "Combo B"]),
    ], False),
]


def main():
    info = api("GET", "system/info?fields=version")
    manifest = {
        "baseUrl": BASE,
        "serverVersion": info.get("version"),
        "objects": [],
    }

    con = pg8000.native.Connection(
        DB_USER, host=DB_HOST, port=DB_PORT, database=DB_NAME, password=DB_PASS
    )

    for collection, table, count, specs, fixable in SEED_PLAN:
        listing = api(
            "GET",
            f"{collection}?fields=id,displayName&order=id:asc&pageSize={count}",
        )
        for obj_ref in listing[collection]:
            uid = obj_ref["id"]
            rows = con.run(
                f"SELECT translations FROM {table} WHERE uid = :uid", uid=uid
            )
            original = rows[0][0] or []
            if isinstance(original, str):
                original = json.loads(original)
            translations = list(original)
            expected = []
            for locale, prop, values in specs:
                translations = [
                    t for t in translations
                    if not (t["locale"] == locale and t["property"] == prop)
                ]
                for value in values:
                    translations.append(
                        {"locale": locale, "property": prop, "value": value}
                    )
                expected.append(
                    {"locale": locale, "property": prop, "values": values}
                )
            con.run(
                f"UPDATE {table} SET translations = :t::jsonb WHERE uid = :uid",
                t=json.dumps(translations),
                uid=uid,
            )
            manifest["objects"].append({
                "collection": collection,
                "id": uid,
                "name": obj_ref["displayName"],
                "fixable": fixable,
                "originalTranslations": original,
                "duplicates": expected,
            })
            print(f"seeded {collection}/{uid} ({obj_ref['displayName']})")

    con.close()

    # Clear server-side caches so the API serves the DB state
    api("POST", "maintenance?cacheClear=true")

    # Verify through the API that the duplicates are visible
    for obj in manifest["objects"]:
        stored = api(
            "GET", f"{obj['collection']}/{obj['id']}?fields=translations"
        ).get("translations", [])
        for dup in obj["duplicates"]:
            got = sorted(
                t["value"] for t in stored
                if t["locale"] == dup["locale"]
                and t["property"] == dup["property"]
            )
            if got != sorted(dup["values"]):
                raise SystemExit(
                    f"SEED VERIFY FAILED {obj['collection']}/{obj['id']} "
                    f"{dup['locale']}/{dup['property']}: API shows {got}, "
                    f"wanted {sorted(dup['values'])}"
                )
    print("API read-back verified: duplicates visible")

    out = sys.argv[1] if len(sys.argv) > 1 else "seed-manifest.json"
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest written to {out}")


if __name__ == "__main__":
    main()
