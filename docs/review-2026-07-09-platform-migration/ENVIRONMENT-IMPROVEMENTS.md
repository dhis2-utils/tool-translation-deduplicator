# Environment & skill improvement suggestions

Collected during the Translation Deduplicator migration + review
(2026-07-09/10, DHIS2 2.40–2.43, Sierra Leone + Laos). Each item:
what happened → what to change. Grouped by where the change belongs.

## 1. Sandbox image / firewall

1. **`apt` is effectively broken on this (ARM) sandbox** — `ports.ubuntu.com`
   is blocked by the egress firewall, so nothing can be installed
   (`postgresql-client` was the concrete need, for DB-level test seeding).
   Either allow `ports.ubuntu.com` in `init-firewall.sh` or preinstall the
   usual suspects in the image: `postgresql-client`, `jq`, `zip`.
   *Workaround that works today: `pip install pg8000 bcrypt` (pure-Python
   Postgres driver + password hashing) — worth documenting as the fallback.*
2. **Git identity is not preconfigured** — the first commit failed with
   "Please tell me who you are". Set `user.name`/`user.email` in the image
   or in the global CLAUDE.md (derivable from the user email already
   provided to agents).
3. **Only one host port is auto-published**, but App Platform dev mode needs
   two for host-side use (dev server :3000 *and* the auth proxy :8080).
   Since dev-server-first is now the preferred workflow (see §5.1), consider
   publishing two ports by default, or a documented convention like
   `agent-sandbox start -p 3000:3000 -p 8080:8080` for DHIS2 app work.

## 2. d2-broker (host-side service)

1. **The 2.41→2.42 in-place upgrade bricks instances**: create-at-41
   instances run Tomcat 9; DHIS2 2.42+ needs Tomcat 10. `POST /upgrade`
   swaps the WAR but not Tomcat, leaving everything 404 with no error. The
   broker should either swap the Tomcat image on upgrades across that
   boundary (like create already does) or refuse with a clear error.
2. **Per-seed credential metadata**: the `lao_hmis_demo_v41` seed ships with
   `admin` *disabled*; discovering that costs a failed-login-cache restart
   cycle. `GET /seeds` could carry a `credentials` / `admin_disabled` hint,
   or the restore step could normalize the admin account.
3. **Instance readiness state**: during boot, `/api/system/info` goes
   through connection-refused → 404 (WAR deploying) → 401/200, and agents
   have to poll and guess. A `status` field on `GET /instances`
   (`deploying` / `migrating` / `ready`) would remove the guesswork.
4. **Pre-migrated seeds**: only a v41 Laos seed exists; testing Laos on
   2.42/2.43 costs a ~10-minute Flyway migration per instance. If Laos
   multi-version testing recurs, add migrated snapshots (like the SL
   per-version seeds).

## 3. `dhis2-instances` skill

1. Document the **Tomcat 9/10 upgrade trap** (§2.1) until the broker fixes
   it: "don't use `/upgrade` across the 2.41→2.42 boundary; create fresh at
   the target version with the older seed — Flyway migrates on boot."
2. Document the **Laos admin-disabled quirk** (§2.2) and the recovery recipe
   (bcrypt UPDATE on `userinfo` + stop/start). The generic "verify
   credentials first" warning exists, but naming the seed saves a cycle.
   The reusable script from this engagement: `tests/e2e/prep_lao_admin.sh`.
3. The skill's DB-access example uses `psql`, which isn't installed and
   can't be installed (§1.1). Add the `pg8000` alternative.

## 4. `dhis2-app-review` skill

1. **Setup-checklist default** *(decision already made — apply it)*: change
   "App Platform — install the built bundle (preferred default)" to
   dev-server-first for consistency with the development workflow, and add
   an explicit review step "verify the zipped bundle builds, installs
   (`POST /api/apps`) and loads — including global-shell integration on
   2.42+". Rationale: the boundary between developing and testing is thin;
   one workflow for both. (Owner preference, 2026-07-10.)
2. **`POST /api/apps` returns 201 on 2.42+** (204 on ≤2.41) — note it in
   `references/version-testing.md`; scripts should accept any 2xx.
3. **`scripts/probe.py` uses `wait_for_load_state("networkidle")`**, which
   times out on apps that fire many requests on load (any scanner/poller).
   Wait on a DOM signal instead, or make the wait strategy a flag.
4. **Seeding data the API refuses to create**: duplicate translations are
   rejected by the API itself (E1106, 2.40+), so test data must be written
   at the DB level (jsonb update → `POST /api/maintenance?cacheClear=true`
   → API read-back). This generalizes to any tool whose target state is
   "legacy data the current server forbids" — worth a short reference
   section. Reusable implementation: `tests/seed_duplicates.py`.
5. **Metadata PUT round-trip pitfalls** (bit both the old and new app;
   generic to admin-tool reviews — worth a reference note):
   - `categoryOptionCombos`: PUT returns bare `200 {"status":"OK"}` but is
     **silently ignored** — verify-after-write is the only detection.
   - `maps` (and likely other types with embedded owned objects): GET
     `:owner` + PUT re-inserts embedded objects → 409 unique-constraint.
   - E1106 means partial fixes of multi-duplicate objects are impossible —
     whole-object atomicity is server-enforced.
6. **Playwright patterns to add** to `references/playwright-patterns.md`:
   - Completion signal via `[data-test='dhis2-uicore-alertbar']`; read the
     text, then wait for `state="detached"` (auto-hide) before the next
     action, or a stale alert matches the next wait.
   - Real-data volumes: don't assert "everything fixed" — some rows
     legitimately remain (server-side limitations); sequential fix flows
     take minutes for hundreds of objects, so completion timeouts must
     scale (suite uses a `FIX_TIMEOUT_MS` env var).
   - Playwright locators can't mix CSS and `text=` engines in one comma
     selector — use `.or_()`.

## 5. Global CLAUDE.md (sandbox-wide)

1. *(Decision already made — apply it)* Add a short routing rule: dev server
   with hot reload is the default for running DHIS2 apps for the user, both
   during development and for manual testing; installing the built zip is a
   verification step for reviews/releases, not the serving mechanism.
   Keep it to 3–4 lines; mechanics stay in the skills.
2. Note that skill edits made *inside* the sandbox don't persist —
   `~/.claude/skills/` is synced from the host, so apply skill changes
   host-side (or sync them back) or they're lost.

## 6. `dhis2-app-dev` skill

1. **TS template gap — `import './locales'`**: the `pnpm create @dhis2/app`
   TypeScript template never registers the app's generated locales, so app
   translations silently don't load (finding M1). Add the import to the
   bootstrapping steps — and consider reporting it upstream against
   `@dhis2/cli-app-scripts`.
2. **i18n extraction pitfalls**: `d2-app-scripts i18n extract`
   (i18next-scanner) silently drops keys containing `:` (parsed as a
   namespace) and keys using the reserved `count` interpolation param.
   Runtime is unaffected (`nsSeparator: false`), so it only surfaces when a
   translator gets an incomplete .pot. Add a rule: no colons in keys, don't
   name a param `count` (unless intentionally using plurals), and diff the
   extracted .pot against `i18n.t()` call sites after adding strings.
3. **Referential stability rule for data hooks**: deriving arrays in a hook
   body (`data?.items.filter(...)`) hands consumers a new identity every
   render; feeding that into a `useEffect` caused finding H1 (a scan
   restart loop measured at 228k requests). Suggested rule: derive with a
   module-level TanStack Query `select` (or `useMemo`) so results are
   referentially stable.
4. **Single-view tool variant**: the bootstrapping guide mandates
   react-router + sidebar + TanStack Table for every app. For single-view
   admin tools, sidebar and table library are overhead — a short "single
   view: keep the hash router with one route, skip sidebar/table-lib"
   note would avoid either blind compliance or ad-hoc deviation.

## 7. Worked well — keep as is

- Broker + per-version seeds + dev-net DB access made 7-configuration
  testing fully self-service; deleting instances per version kept within
  resource limits.
- The review skill's install-zip path *as a verification step* caught real
  integration facts (global-shell iframe on 2.42+, manifest/icon handling).
- Basic-auth `GET /api/me` cookie injection for Playwright worked first
  time on every version, as documented.
- `pnpm create @dhis2/app` scaffold + `@dhis2/ui` source-reading workflow
  (props verified against `node_modules` types) produced zero UI-prop bugs.
- The adversarial-review subagent pattern: 1 real critical catch (H1), 1
  false alarm (PATCH claim) — the skill's "verify HIGH claims in framework
  source before filing" rule did its job.
