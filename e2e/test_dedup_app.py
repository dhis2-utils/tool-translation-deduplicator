#!/usr/bin/env python3
"""End-to-end suite for the Translation Deduplication Tool.

Called by e2e/run.sh, which documents the inputs. Installs the app, seeds
its own objects with duplicate translations, drives the app in Chromium,
checks every write against the API, cleans up, uninstalls the app and
writes $RESULTS_DIR/results.json.

WARNING: changes and deletes data. Throwaway instances only.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

import dhis2_api as d2

CONTRACT_VERSION = 1
SCAN_TIMEOUT_MS = int(os.environ.get("SCAN_TIMEOUT_MS", "600000"))
FIX_TIMEOUT_MS = int(os.environ.get("FIX_TIMEOUT_MS", "600000"))
FRAME_TIMEOUT_S = 90

SEL_FIX_BUTTON = "[data-test='fix-selected-button']"
SEL_RESCAN_BUTTON = "[data-test='rescan-button']"
SEL_SCAN_PROGRESS = "[data-test='scan-progress']"
SEL_NOTICE = "[data-test='dhis2-uicore-noticebox']"
SEL_ALERT = "[data-test='dhis2-uicore-alertbar']"
SEL_ALERT_DISMISS = "[data-test='dhis2-uicore-alertbar-dismiss']"
SEL_FIX_ERRORS = "[data-test='fix-errors-notice']"
SEL_SELECT_ALL = "[data-test='select-all-checkbox'] input"
SEL_ROW_CHECKBOX = "[data-test='row-checkbox'] input"
SEL_ANY_ROW = "[data-test^='duplicate-row-']"
TEXT_NO_DUPLICATES = "No duplicate translations found"
TEXT_UNFIXABLE = "Cannot be fixed via API"

# Requests that fail on any instance without a custom logo; not app errors.
IGNORED_HTTP_ERRORS = ("staticContent/logo_banner", "favicon", "manifest.json")

# Seeded objects the app can fix, and the ones it must leave alone.
FIXABLE = [
    ("dataElements", "de_a"),
    ("dataElements", "de_b"),
    ("dataElements", "de_locked"),
    ("dataSets", "ds"),
    ("optionSets", "os"),
    ("options", "opt"),
    ("categoryOptions", "co"),
]


class Suite:
    def __init__(self, config):
        self.config = config
        self.api = d2.Dhis2(config["url"], config["user"], config["password"])
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self.xss_value = f'<img src="x-e2e-{self.run_id}" onerror="window.__e2eXss=1">'
        self.low_password = f"E2e-{d2.new_uid()}-1!"
        self.tests = []
        self.uid = {}
        self.coc_id = None
        self.expected = {}  # (collection, id) -> {(locale, property): [values]}
        self.snapshots = {}
        self.kept_value = None
        self.page_errors = []
        self.http_errors = []
        self.frame = None
        self.page = None

    # --- bookkeeping ---------------------------------------------------

    def record(self, test_id, status, message=""):
        self.tests.append({"id": test_id, "status": status, "message": message})
        print(f"[{self.config['label']}] {status.upper()}: {test_id}"
              + (f" ({message})" if message else ""), flush=True)

    def screenshot(self, name):
        try:
            self.page.screenshot(path=str(Path(self.config["results_dir"]) / f"{name}.png"),
                                 full_page=True)
        except Exception as error:  # a screenshot must never fail a run
            print(f"screenshot {name} failed: {error}")

    def obj(self, collection, key):
        return collection, self.uid[key]

    # --- setup ---------------------------------------------------------

    def seed(self):
        d2.clean_previous_run(self.api)
        self.uid, stages = d2.plan_seed(self.run_id, self.xss_value)
        # Record every object before creating it, so an interrupted run
        # can be cleaned up by the next one.
        d2.write_state(self.api, {"runId": self.run_id, "objects": d2.records_for(self.uid)})
        for stage in stages:
            d2.import_metadata(self.api, stage)
        self.coc_id = d2.seed_coc_duplicates(self.api, self.uid["cc"])
        d2.create_low_privilege_user(self.api, self.uid, self.run_id, self.low_password,
                                     self.config["app_key"])
        self.api.request("POST", "maintenance?cacheClear=true")

        seeded = [*(self.obj(c, k) for c, k in FIXABLE),
                  self.obj("maps", "map"), ("categoryOptionCombos", self.coc_id)]
        for collection, object_id in seeded:
            duplicates = d2.duplicates_of(self.api, collection, object_id)
            if not duplicates:
                raise RuntimeError(f"seed read-back: no duplicates on {collection}/{object_id}")
            self.expected[(collection, object_id)] = duplicates
        for collection, key in FIXABLE:
            self.snapshots[self.obj(collection, key)] = d2.owner_snapshot(
                self.api, collection, self.uid[key])

    # --- browser helpers -----------------------------------------------

    def open_app(self, browser, api):
        name, value = api.session_cookie()
        host = self.config["url"].split("://", 1)[1].split("/", 1)[0].split(":")[0]
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        context.add_cookies([{"name": name, "value": value, "domain": host, "path": "/"}])
        page = context.new_page()
        page.goto(f"{self.config['url']}/api/apps/{self.config['app_key']}/index.html")
        return page, find_app_frame(page)

    def row(self, object_id, locale, prop):
        return self.frame.locator(f"[data-test='duplicate-row-{object_id}-{locale}-{prop}']")

    def object_rows(self, object_id, frame=None):
        return (frame or self.frame).locator(f"[data-test^='duplicate-row-{object_id}-']")

    def check_object(self, object_id, frame=None):
        self.object_rows(object_id, frame).locator(SEL_ROW_CHECKBOX).first.check(force=True)

    def wait_for_scan(self, frame=None):
        frame = frame or self.frame
        frame.locator(SEL_FIX_BUTTON).or_(frame.get_by_text(TEXT_NO_DUPLICATES)).first.wait_for(
            timeout=SCAN_TIMEOUT_MS)

    def click_fix_and_read_alert(self, frame=None):
        frame = frame or self.frame
        frame.locator(SEL_FIX_BUTTON).click()
        alert = frame.locator(SEL_ALERT).first
        alert.wait_for(timeout=FIX_TIMEOUT_MS)
        text = alert.inner_text()
        # Success alerts hide themselves; critical ones stay until dismissed.
        # Wait for it to go, or the next wait matches this alert.
        if "failed" in text:
            alert.locator(SEL_ALERT_DISMISS).click()
        alert.wait_for(state="detached", timeout=60000)
        return text

    # --- tests ---------------------------------------------------------

    def test_app_loads(self, browser):
        self.page, self.frame = self.open_app(browser, self.api)
        self.page.on("pageerror", lambda e: self.page_errors.append(str(e)))
        self.page.on("response", lambda r: self.http_errors.append(f"{r.status} {r.url}")
                     if r.status >= 400 else None)
        in_iframe = self.frame != self.page.main_frame
        self.record("app-loads", "pass", f"global-shell iframe: {in_iframe}")

    def test_scan_completes(self):
        self.wait_for_scan()
        self.screenshot("scan-done")
        self.record("scan-completes", "pass",
                    f"{self.frame.locator(SEL_ANY_ROW).count()} rows")

    def test_seeded_rows_listed(self):
        missing = [
            f"{oid}/{locale}/{prop}"
            for (_, oid), groups in self.expected.items()
            for (locale, prop) in groups
            if not self.row(oid, locale, prop).count()
        ]
        self.record("seeded-rows-listed", "fail" if missing else "pass",
                    f"missing: {missing}" if missing else f"{len(self.expected)} objects")

    def test_html_shown_as_text(self):
        injected = self.frame.locator(f"img[src='x-e2e-{self.run_id}']").count()
        executed = self.frame.evaluate("window.__e2eXss")
        shown = self.frame.get_by_text(self.xss_value, exact=True).count()
        ok = injected == 0 and executed is None and shown > 0
        self.record("html-shown-as-text", "pass" if ok else "fail",
                    f"img elements: {injected}, handler ran: {executed}, shown as text: {shown}")

    def test_unfixable_flagged(self):
        problems = []
        for oid in (self.uid["map"], self.coc_id):
            rows = self.object_rows(oid)
            has_checkbox = rows.locator(SEL_ROW_CHECKBOX).count()
            has_tag = rows.filter(has_text=TEXT_UNFIXABLE).count()
            if has_checkbox or not has_tag:
                problems.append(f"{oid}: checkbox={has_checkbox}, tag={has_tag}")
        self.record("unfixable-flagged", "fail" if problems else "pass", "; ".join(problems))

    def test_select_all_toggles(self):
        select_all = self.frame.locator(SEL_SELECT_ALL)
        select_all.check(force=True)
        boxes = self.frame.locator(SEL_ROW_CHECKBOX)
        total, checked = boxes.count(), self.frame.locator(f"{SEL_ROW_CHECKBOX}:checked").count()
        select_all.uncheck(force=True)
        after = self.frame.locator(f"{SEL_ROW_CHECKBOX}:checked").count()
        ok = total > 0 and checked == total and after == 0
        self.record("select-all-toggles", "pass" if ok else "fail",
                    f"checked {checked}/{total}, after clearing: {after}")

    def test_object_selected_as_whole(self):
        de_a = self.uid["de_a"]
        pairs = len(self.expected[("dataElements", de_a)])
        self.check_object(de_a)
        label = self.frame.locator(SEL_FIX_BUTTON).inner_text()
        self.record("object-selected-as-whole", "pass" if f"({pairs})" in label else "fail",
                    label)

    def test_choose_value(self):
        values = self.expected[("dataElements", self.uid["de_a"])][("fr", "NAME")]
        # the app lists values in the order the server returns them
        self.kept_value = values[1]
        self.row(self.uid["de_a"], "fr", "NAME").get_by_role("radio").nth(1).check(force=True)
        self.record("choose-value", "pass", self.kept_value)

    def test_fix_single_object(self):
        alert = self.click_fix_and_read_alert()
        no_errors = not self.frame.locator(SEL_FIX_ERRORS).count()
        gone = not self.object_rows(self.uid["de_a"]).count()
        ok = "failed" not in alert and no_errors and gone
        self.screenshot("fix-single")
        self.record("fix-single-object", "pass" if ok else "fail",
                    f"alert: {alert!r}, rows gone: {gone}")

    def test_permission_refused(self, browser):
        low = d2.Dhis2(self.config["url"], f"e2e-ttd-{self.run_id.lower()}", self.low_password)
        page, frame = self.open_app(browser, low)
        try:
            self.wait_for_scan(frame)
            locked = self.uid["de_locked"]
            self.check_object(locked, frame)
            alert = self.click_fix_and_read_alert(frame)
            notice = frame.locator(SEL_FIX_ERRORS)
            listed = notice.count() and locked in notice.inner_text()
            unchanged = d2.duplicates_of(self.api, "dataElements", locked) == \
                self.expected[("dataElements", locked)]
            page.screenshot(path=str(Path(self.config["results_dir"]) / "permission.png"),
                            full_page=True)
            ok = "failed" in alert and bool(listed) and unchanged
            self.record("permission-refused", "pass" if ok else "fail",
                        f"alert: {alert!r}, object listed: {bool(listed)}, "
                        f"data unchanged: {unchanged}")
        finally:
            page.context.close()

    def test_fix_seeded_objects(self):
        targets = [self.uid[k] for _, k in FIXABLE if k != "de_a"]
        for oid in targets:
            self.check_object(oid)
        alert = self.click_fix_and_read_alert()
        no_errors = not self.frame.locator(SEL_FIX_ERRORS).count()
        left = [oid for oid in targets if self.object_rows(oid).count()]
        self.screenshot("fix-seeded")
        ok = "failed" not in alert and no_errors and not left
        self.record("fix-seeded-objects", "pass" if ok else "fail",
                    f"alert: {alert!r}, still listed: {left}")

    def test_api_state(self):
        problems = []
        for collection, key in FIXABLE:
            remaining = d2.duplicates_of(self.api, collection, self.uid[key])
            if remaining:
                problems.append(f"{collection}/{self.uid[key]} still has {remaining}")
        stored = self.api.get(f"dataElements/{self.uid['de_a']}?fields=translations")
        kept = [t["value"] for t in stored.get("translations", [])
                if t["locale"] == "fr" and t["property"] == "NAME"]
        if kept != [self.kept_value]:
            problems.append(f"chosen value not kept: {kept} != [{self.kept_value!r}]")
        for collection, oid in (("maps", self.uid["map"]), ("categoryOptionCombos", self.coc_id)):
            if d2.duplicates_of(self.api, collection, oid) != self.expected[(collection, oid)]:
                problems.append(f"unfixable {collection}/{oid} was changed")
        self.record("api-state", "fail" if problems else "pass", "; ".join(problems))

    def test_owner_fields_unchanged(self):
        changed = [
            f"{collection}/{oid}"
            for (collection, oid), before in self.snapshots.items()
            if d2.owner_snapshot(self.api, collection, oid) != before
        ]
        self.record("owner-fields-unchanged", "fail" if changed else "pass",
                    f"changed: {changed}" if changed else f"{len(self.snapshots)} objects")

    def test_rescan_clean(self):
        self.frame.locator(SEL_RESCAN_BUTTON).click()
        self.frame.locator(SEL_SCAN_PROGRESS).or_(self.frame.locator(SEL_ANY_ROW)).first.wait_for(
            timeout=60000)
        self.wait_for_scan()
        listed = [self.uid[k] for _, k in FIXABLE if self.object_rows(self.uid[k]).count()]
        unfixable_kept = all(self.object_rows(oid).count()
                             for oid in (self.uid["map"], self.coc_id))
        self.screenshot("rescan")
        ok = not listed and unfixable_kept
        self.record("rescan-clean", "pass" if ok else "fail",
                    f"fixed objects still listed: {listed}, unfixable still listed: "
                    f"{unfixable_kept}")

    def test_no_page_errors(self):
        http = [e for e in self.http_errors
                if not any(s in e for s in IGNORED_HTTP_ERRORS)]
        ok = not self.page_errors and not http
        self.record("no-page-errors", "pass" if ok else "fail",
                    f"page errors: {self.page_errors[:3]}, http: {http[:5]}")

    # --- run -----------------------------------------------------------

    def run_browser_tests(self):
        steps = [
            ("app-loads", lambda b: self.test_app_loads(b)),
            ("scan-completes", lambda b: self.test_scan_completes()),
            ("seeded-rows-listed", lambda b: self.test_seeded_rows_listed()),
            ("html-shown-as-text", lambda b: self.test_html_shown_as_text()),
            ("unfixable-flagged", lambda b: self.test_unfixable_flagged()),
            ("select-all-toggles", lambda b: self.test_select_all_toggles()),
            ("object-selected-as-whole", lambda b: self.test_object_selected_as_whole()),
            ("choose-value", lambda b: self.test_choose_value()),
            ("fix-single-object", lambda b: self.test_fix_single_object()),
            ("permission-refused", lambda b: self.test_permission_refused(b)),
            ("fix-seeded-objects", lambda b: self.test_fix_seeded_objects()),
            ("api-state", lambda b: self.test_api_state()),
            ("owner-fields-unchanged", lambda b: self.test_owner_fields_unchanged()),
            ("rescan-clean", lambda b: self.test_rescan_clean()),
            ("no-page-errors", lambda b: self.test_no_page_errors()),
        ]
        # Steps up to the scan are prerequisites: if one fails, skip the rest.
        blocking = {"app-loads", "scan-completes"}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for index, (test_id, step) in enumerate(steps):
                    try:
                        step(browser)
                    except Exception as error:
                        self.screenshot(f"{test_id}-error")
                        self.record(test_id, "fail", f"{type(error).__name__}: {error}")
                        if test_id in blocking:
                            for skipped, _ in steps[index + 1:]:
                                self.record(skipped, "skip", f"{test_id} failed")
                            break
            finally:
                browser.close()

    def cleanup(self):
        state = d2.read_state(self.api)
        leftovers = d2.delete_objects(self.api, state.get("objects", []) if state else [])
        if leftovers:
            print(f"cleanup: could not delete {leftovers}; kept in "
                  f"{d2.STATE_NAMESPACE}/{d2.STATE_KEY} for the next run")
        else:
            d2.delete_state(self.api)
        d2.uninstall_app(self.api, self.config["app_key"])
        return leftovers


def find_app_frame(page):
    """The app is served top-level on 2.41 and earlier, and inside the
    global-shell iframe on 2.42 and later."""
    deadline = time.time() + FRAME_TIMEOUT_S
    marker = f"{SEL_SCAN_PROGRESS}, {SEL_FIX_BUTTON}, {SEL_NOTICE}"
    while time.time() < deadline:
        for frame in page.frames:
            try:
                if frame.locator(marker).count():
                    return frame
            except Exception:
                continue
        page.wait_for_timeout(1000)
    raise RuntimeError("app frame not found: the scan UI never appeared")


def read_config():
    missing = [v for v in ("DHIS2_URL", "DHIS2_USER", "DHIS2_PASS", "APP_ZIP", "RESULTS_DIR")
               if not os.environ.get(v)]
    if missing:
        print(f"missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)
    return {
        "url": os.environ["DHIS2_URL"].rstrip("/"),
        "user": os.environ["DHIS2_USER"],
        "password": os.environ["DHIS2_PASS"],
        "zip": os.environ["APP_ZIP"],
        "results_dir": os.environ["RESULTS_DIR"],
        "label": os.environ.get("LABEL", ""),
        "app_key": os.environ.get("APP_KEY", ""),
    }


def write_results(suite, started, server_version, app_version, error=None):
    tests = suite.tests if error is None else []
    results = {
        "contract_version": CONTRACT_VERSION,
        "label": suite.config["label"],
        "server_version": server_version,
        "app_key": suite.config["app_key"],
        "app_version": app_version,
        "duration_s": round(time.time() - started),
        "total": len(tests),
        "passed": sum(t["status"] == "pass" for t in tests),
        "failed": sum(t["status"] == "fail" for t in tests),
        "skipped": sum(t["status"] == "skip" for t in tests),
        "tests": tests,
    }
    if error:
        results["error"] = error
    path = Path(suite.config["results_dir"]) / "results.json"
    path.write_text(json.dumps(results, indent=2))
    return results


def main():
    started = time.time()
    suite = Suite(read_config())
    server_version = app_version = ""
    stage = "setup"
    try:
        server_version = suite.api.get("system/info")["version"]
        suite.config["label"] = suite.config["label"] or server_version
        manifest = d2.read_manifest(suite.config["zip"])
        app_version = manifest.get("version", "")
        stage = "install"
        installed_key = d2.install_app(suite.api, suite.config["zip"], manifest["name"])
        suite.config["app_key"] = suite.config["app_key"] or installed_key
        stage = "seeding"
        suite.seed()
    except Exception as error:
        message = f"{stage} failed: {type(error).__name__}: {error}"
        print(message, file=sys.stderr)
        try:
            if suite.config["app_key"]:
                suite.cleanup()
        except Exception as cleanup_error:
            print(f"cleanup failed: {cleanup_error}", file=sys.stderr)
        write_results(suite, started, server_version, app_version, error=message)
        return 2

    try:
        suite.run_browser_tests()
    finally:
        leftovers = suite.cleanup()
    suite.record("cleanup", "fail" if leftovers else "pass",
                 f"left behind: {leftovers}" if leftovers else "")
    results = write_results(suite, started, server_version, app_version)
    print(f"[{suite.config['label']}] {results['passed']}/{results['total']} passed, "
          f"{results['failed']} failed, {results['skipped']} skipped"
          + (f"; cleanup left {len(leftovers)} objects" if leftovers else ""))
    return 1 if results["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
