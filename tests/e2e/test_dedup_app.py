#!/usr/bin/env python3
"""End-to-end test suite for the Translation Deduplication Tool.

Runs against a live DHIS2 instance on which the app is installed and
`tests/seed_duplicates.py` has been run. Verifies the full flow:
scan -> table contents -> radio choice -> fix selected -> API state.

Usage:
    DHIS2_URL=http://dhis2-agent-td40:8080 DHIS2_USER=admin DHIS2_PASS=district \
    LABEL=2.40-sl SEED_MANIFEST=seed-manifest.json \
        python3 tests/e2e/test_dedup_app.py

Results: tests/e2e/output/<LABEL>/results.json + step screenshots.
WARNING: mutates data — only run against disposable instances.
"""

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("DHIS2_URL", "http://localhost:8080").rstrip("/")
USER = os.environ.get("DHIS2_USER", "admin")
PASS = os.environ.get("DHIS2_PASS", "district")
LABEL = os.environ.get("LABEL", "unlabelled")
APP_KEY = os.environ.get("APP_KEY", "tool-translation-deduplicator")
MANIFEST = os.environ.get("SEED_MANIFEST", "seed-manifest.json")
SCAN_TIMEOUT_MS = int(os.environ.get("SCAN_TIMEOUT_MS", "300000"))

OUT = Path(__file__).parent / "output" / LABEL
OUT.mkdir(parents=True, exist_ok=True)

AUTH = "Basic " + base64.b64encode(f"{USER}:{PASS}".encode()).decode()

results = []
console_log = []
page_errors = []
http_errors = []


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{BASE}/api/{path}",
        method=method,
        headers={"Authorization": AUTH, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or "{}")


def get_session_cookie():
    req = urllib.request.Request(
        f"{BASE}/api/me", headers={"Authorization": AUTH}
    )
    with urllib.request.urlopen(req) as r:
        for c in r.headers.get_all("Set-Cookie") or []:
            head = c.split(";", 1)[0]
            name, _, value = head.partition("=")
            if "JSESSIONID" in name:
                return name.strip(), value.strip()
    raise RuntimeError("No JSESSIONID cookie returned by /api/me")


def record(step, status, detail=""):
    results.append({"step": step, "status": status, "detail": detail})
    print(f"[{LABEL}] {status}: {step}" + (f" — {detail}" if detail else ""))


def find_app_frame(page):
    """The app may be served top-level (<=2.41) or inside the global
    shell iframe (2.42+). Return the frame containing the app root."""
    deadline = time.time() + 60
    while time.time() < deadline:
        for frame in page.frames:
            try:
                if frame.locator(
                    "[data-test='scan-progress'], [data-test='fix-selected-button'],"
                    " [data-test='dhis2-uicore-noticebox']"
                ).count():
                    return frame
            except Exception:
                continue
        page.wait_for_timeout(1000)
    raise RuntimeError("App frame not found (scan UI never appeared)")


def main():
    manifest = json.loads(Path(MANIFEST).read_text())
    seeded = manifest["objects"]

    server_version = api("GET", "system/info?fields=version")["version"]
    record("server version", "INFO", server_version)

    cookie_name, cookie_value = get_session_cookie()
    host = BASE.split("://", 1)[1].split(":")[0]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
        ctx.add_cookies([{
            "name": cookie_name,
            "value": cookie_value,
            "domain": host,
            "path": "/",
        }])
        page = ctx.new_page()
        page.on("console", lambda m: console_log.append((m.type, m.text)))
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on(
            "response",
            lambda r: http_errors.append((r.status, r.url))
            if r.status >= 400 else None,
        )

        # --- Step 1: app loads and scan starts
        page.goto(f"{BASE}/api/apps/{APP_KEY}/index.html")
        try:
            frame = find_app_frame(page)
            in_iframe = frame != page.main_frame
            record("app loads", "PASS", f"iframe={in_iframe}")
        except Exception as e:
            page.screenshot(path=str(OUT / "01-load-FAIL.png"), full_page=True)
            record("app loads", "FAIL", str(e))
            raise
        page.screenshot(path=str(OUT / "01-load.png"), full_page=True)

        # --- Step 2: scan completes
        try:
            frame.locator("[data-test='fix-selected-button']").wait_for(
                timeout=SCAN_TIMEOUT_MS
            )
            record("scan completes with duplicates found", "PASS")
        except Exception as e:
            page.screenshot(path=str(OUT / "02-scan-FAIL.png"), full_page=True)
            record("scan completes with duplicates found", "FAIL", str(e))
            raise
        page.screenshot(path=str(OUT / "02-scan-done.png"), full_page=True)

        # --- Step 3: all seeded duplicates are listed
        def row_sel(obj_id, locale, prop):
            return f"[data-test='duplicate-row-{obj_id}-{locale}-{prop}']"

        rows = frame.locator("[data-test^='duplicate-row-']")
        row_count = rows.count()
        missing = []
        for obj in seeded:
            for dup in obj["duplicates"]:
                if not frame.locator(
                    row_sel(obj["id"], dup["locale"], dup["property"])
                ).count():
                    missing.append(f"{obj['id']}/{dup['locale']}/{dup['property']}")
        if missing:
            record("seeded duplicates listed", "FAIL", f"missing: {missing}")
        else:
            record(
                "seeded duplicates listed", "PASS",
                f"{row_count} rows total",
            )

        # --- Step 3b: unfixable types are flagged and not selectable
        unfixable_objs = [o for o in seeded if not o.get("fixable", True)]
        if unfixable_objs:
            problems = []
            for obj in unfixable_objs:
                obj_rows = f"[data-test^='duplicate-row-{obj['id']}-']"
                has_checkbox = frame.locator(
                    f"{obj_rows} [data-test='row-checkbox']"
                ).count()
                has_tag = frame.locator(
                    obj_rows, has_text="Cannot be fixed via API"
                ).count()
                if has_checkbox or not has_tag:
                    problems.append(
                        f"{obj['id']}: checkbox={has_checkbox}, tag={has_tag}"
                    )
            record(
                "unfixable types flagged, not selectable",
                "FAIL" if problems else "PASS",
                "; ".join(problems) or f"{len(unfixable_objs)} object(s)",
            )

        # --- Step 4: pick the second value for the first seeded DE NAME row
        target = seeded[0]
        name_dup = next(
            d for d in target["duplicates"] if d["property"] == "NAME"
        )
        keep_value = name_dup["values"][1]  # choose the non-default option
        target_row = frame.locator(
            row_sel(target["id"], name_dup["locale"], "NAME")
        )
        try:
            target_row.get_by_role("radio").nth(1).check(force=True)
            record("choose non-default translation", "PASS", keep_value)
        except Exception as e:
            record("choose non-default translation", "FAIL", str(e))
        page.screenshot(path=str(OUT / "03-radio.png"), full_page=True)

        # --- Step 4b: selecting one row selects its whole object
        # (objects can only be fixed atomically — E1106), and fixing a
        # single multi-pair object succeeds with no failures.
        target_pairs = len(target["duplicates"])
        frame.locator(
            f"[data-test^='duplicate-row-{target['id']}-'] "
            "[data-test='row-checkbox'] input"
        ).first.check(force=True)
        button_label = frame.locator(
            "[data-test='fix-selected-button']"
        ).inner_text()
        if f"({target_pairs})" in button_label:
            record("partial selection selects whole object", "PASS",
                   button_label)
        else:
            record("partial selection selects whole object", "FAIL",
                   f"expected ({target_pairs}) in {button_label!r}")
        frame.locator("[data-test='fix-selected-button']").click()
        alert = frame.locator("[data-test='dhis2-uicore-alertbar']")
        try:
            alert.first.wait_for(timeout=120000)
            alert_text = alert.first.inner_text()
            no_error_notice = not frame.locator(
                "[data-test='fix-errors-notice']"
            ).count()
            target_rows_gone = not frame.locator(
                f"[data-test^='duplicate-row-{target['id']}-']"
            ).count()
            ok = "failed" not in alert_text and no_error_notice and target_rows_gone
            record("fix single multi-pair object", "PASS" if ok else "FAIL",
                   f"alert: {alert_text!r}, rows gone: {target_rows_gone}")
            alert.first.wait_for(state="detached", timeout=30000)
        except Exception as e:
            page.screenshot(path=str(OUT / "04b-partial-FAIL.png"), full_page=True)
            record("fix single multi-pair object", "FAIL", str(e))
        page.screenshot(path=str(OUT / "04b-partial-fixed.png"), full_page=True)
        row_count = frame.locator("[data-test^='duplicate-row-']").count()

        # --- Step 5: select all remaining rows and fix
        frame.locator("[data-test='select-all-checkbox'] input").check(
            force=True
        )
        checkboxes = frame.locator("[data-test='row-checkbox'] input").count()
        checked = frame.locator(
            "[data-test='row-checkbox'] input:checked"
        ).count()
        if checked == checkboxes:
            record("select all", "PASS", f"{checked}/{checkboxes} objects")
        else:
            record("select all", "FAIL", f"{checked}/{checkboxes} objects")
        page.screenshot(path=str(OUT / "04-selected.png"), full_page=True)

        frame.locator("[data-test='fix-selected-button']").click()
        # Completion signal = the result alert bar. With real-world data
        # volumes (hundreds of rows) the sequential fix can take minutes,
        # and rows that fail server-side validation legitimately remain.
        fix_timeout = int(os.environ.get("FIX_TIMEOUT_MS", "600000"))
        try:
            alert = frame.locator("[data-test='dhis2-uicore-alertbar']")
            alert.first.wait_for(timeout=fix_timeout)
            alert_text = alert.first.inner_text()
            leftover = frame.locator("[data-test^='duplicate-row-']").count()
            record(
                "fix selected completes", "PASS",
                f"alert: {alert_text!r}, rows remaining: {leftover}",
            )
        except Exception as e:
            page.screenshot(path=str(OUT / "05-fix-FAIL.png"), full_page=True)
            record("fix selected completes", "FAIL", str(e))
        page.screenshot(path=str(OUT / "05-fixed.png"), full_page=True)

        # --- Step 6: verify via API that duplicates are gone and the
        # chosen value was kept
        api_failures = []
        for obj in seeded:
            stored = api(
                "GET",
                f"{obj['collection']}/{obj['id']}?fields=translations",
            ).get("translations", [])
            # unfixable objects (no checkbox) are never touched, so their
            # duplicates must still be present
            expected_count = 1 if obj.get("fixable", True) else None
            for dup in obj["duplicates"]:
                remaining = [
                    t["value"] for t in stored
                    if t["locale"] == dup["locale"]
                    and t["property"] == dup["property"]
                ]
                expected = expected_count or len(dup["values"])
                if len(remaining) != expected:
                    api_failures.append(
                        f"{obj['id']} {dup['locale']}/{dup['property']}: "
                        f"{len(remaining)} translations remain "
                        f"(expected {expected}): {remaining}"
                    )
        # the explicitly chosen value must be the one kept
        stored = api(
            "GET",
            f"{target['collection']}/{target['id']}?fields=translations",
        ).get("translations", [])
        kept = [
            t["value"] for t in stored
            if t["locale"] == name_dup["locale"] and t["property"] == "NAME"
        ]
        if kept != [keep_value]:
            api_failures.append(
                f"chosen value not kept for {target['id']}: {kept} != [{keep_value}]"
            )
        if api_failures:
            record("API state after fix", "FAIL", "; ".join(api_failures))
        else:
            record("API state after fix", "PASS")

        # --- Step 7: rescan no longer lists the seeded duplicates
        # (pre-existing unfixable rows, e.g. maps failing server-side,
        # may legitimately remain on real-world databases)
        frame.locator("[data-test='rescan-button']").click()
        try:
            frame.locator("[data-test='fix-selected-button']").or_(
                frame.get_by_text("No duplicate translations found")
            ).first.wait_for(timeout=SCAN_TIMEOUT_MS)
            still_listed = [
                obj["id"] for obj in seeded
                if obj.get("fixable", True) and frame.locator(
                    f"[data-test^='duplicate-row-{obj['id']}-']"
                ).count()
            ]
            leftover = frame.locator("[data-test^='duplicate-row-']").count()
            if still_listed:
                record(
                    "rescan: seeded duplicates gone", "FAIL",
                    f"still listed: {still_listed}",
                )
            else:
                record(
                    "rescan: seeded duplicates gone", "PASS",
                    f"{leftover} pre-existing rows remain",
                )
        except Exception as e:
            page.screenshot(path=str(OUT / "06-rescan-FAIL.png"), full_page=True)
            record("rescan: seeded duplicates gone", "FAIL", str(e))
        page.screenshot(path=str(OUT / "06-rescan.png"), full_page=True)

        browser.close()

    summary = {
        "label": LABEL,
        "serverVersion": server_version,
        "results": results,
        "pageErrors": page_errors,
        "consoleErrors": [m for m in console_log if m[0] == "error"],
        "httpErrors": [
            e for e in http_errors
            # ignore benign 404s for optional resources
            if not any(s in e[1] for s in ("favicon", "manifest.json"))
        ],
    }
    (OUT / "results.json").write_text(json.dumps(summary, indent=2))
    failed = [r for r in results if r["status"] == "FAIL"]
    print(f"\n[{LABEL}] {len(results) - len(failed) - 1}/{len(results) - 1} steps passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
