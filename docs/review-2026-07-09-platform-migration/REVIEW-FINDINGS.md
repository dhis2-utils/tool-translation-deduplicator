# Review findings: Translation Deduplicator Tool v1.0.0 (App Platform migration)

Reviewed: 2026-07-09 · Scope: migration + code review + functional test (DHIS2 2.40–2.43, Sierra Leone + Laos) · Reviewer: agent (Claude Fable 5, Claude Code)
DHIS2 versions tested: 2.40.12, 2.41.9, 2.42.x, 2.43.x (see UI-TEST-RESULTS.md)

## Summary

The app was migrated from the vanilla webpack/materialize tool-template to the
DHIS2 App Platform (React 18 + TypeScript + `@dhis2/app-runtime` + `@dhis2/ui`)
on branch `app-platform-migration`. Two serious defects were found and fixed
*during* the review of the migrated code (one would have flooded the server
with requests; both were caught before any release). The final build passes
the full e2e flow — scan, select, fix, verify via API, rescan — on all tested
versions and both demo databases.

## Findings

All findings below were **fixed during this engagement** unless marked open.

### HIGH

#### H1. Scan-restart loop flooded the server with requests (fixed)

- **Where**: `src/hooks/useTranslatableSchemas.ts` (pre-fix), `src/hooks/useDuplicateScan.ts:99`
- **What**: the hook returned `data?.schemas.filter(...)` — a new array identity
  on every render — and the scan `useEffect` depends on it. Every `setState`
  from the scan re-triggered the effect, which cancelled and restarted the
  scan. Measured live on 2.40: **228,466 API requests in ~5 minutes**, scan
  never completed, `net::ERR_INSUFFICIENT_RESOURCES` in the console.
- **Fix**: memoized via a module-level TanStack Query `select` function so the
  filtered array is referentially stable (commit `c03acb9`). Verified live:
  84 requests total, scan completes.

### MEDIUM

#### M1. App translations were never registered (fixed)

- **Where**: `src/App.tsx`
- **What**: the `@dhis2/app` TypeScript template does not emit
  `import './locales'`, so the generated i18n resources were never loaded.
  English works by accident (keys are natural-language English); any other
  locale would silently fall back.
- **Fix**: added `import './locales'` to `App.tsx` (commit `c03acb9`).

#### M2. i18n string extraction silently skipped two strings (fixed)

- **Where**: `src/pages/DuplicatesPage.tsx`
- **What**: `d2-app-scripts i18n extract` (i18next-scanner) treats `:` inside a
  key as a namespace separator and mishandles the reserved `count`
  interpolation param — `'Fix selected ({{count}})'` and the skipped-types
  message were missing from `i18n/en.pot`. Runtime rendering was unaffected
  (d2-i18n sets `nsSeparator: false`), so this only breaks translatability.
- **Fix**: rephrased to avoid `:` in keys and renamed `count` → `selected`
  (commit `c03acb9`). Both strings now extract.

### Defects in the pre-migration (v0.2.0) app, resolved by the migration

- **Selecting between identical duplicate values re-introduced both**
  (`src/app.js:119-129`, old code): radio keys were `locale-property-value`,
  so two identical values shared a key and both got `selectedValue` set,
  re-creating the duplicate on save. Moot in practice — see note N1 — but the
  new index-based radio selection cannot hit this.
- **Stale selection state after fixing** (`src/app.js:105-115`, old code):
  `selectedDuplicates` was not pruned after a successful fix, so the
  "select all" checkbox state could be computed incorrectly afterwards. The
  new app prunes fixed keys from the selection.
- **Silently skipped object types** (`src/app.js:25-33`, old code): a type
  that failed to fetch (e.g. no read access) was silently dropped. The new
  app lists skipped types in a warning notice (a limitation the MANUAL
  previously only warned about in prose).
- **Version-sniffing header-bar hack** (`src/js/check-header-bar.js`, old
  code): custom `version.minor < 42` logic to load the legacy header bar.
  Gone — the App Platform provides the header bar on 2.40/2.41 and
  integrates with the global shell on 2.42+ (verified on all four versions).

### LOW

#### L1. No sorting or paging in the duplicates table — `src/components/DuplicatesTable.tsx`

Rows render in schema-scan order. Fine for the typical handful of duplicates;
an instance with hundreds of legacy duplicates would get one long unsorted
table. Consider `DataTableColumnHeader` sorting if that becomes a real case.

#### L2. Scan fetches every object of every translatable type with `paging=false`

Same behavior as v0.2.0. On the Laos demo (larger DB) the scan still
completes (see UI-TEST-RESULTS.md) but transfers the full metadata set.
A server-side filter is not available for "has duplicate translations", so
this is inherent to the approach; a `filter=translations:!empty`-style
optimization is not reliable across 2.40–2.43 and was deliberately not used.

## Notes on server behavior (informative, drove test design)

#### N1. Duplicate translations cannot be created through the API since 2.40

`PUT` with duplicate (locale, property) pairs is rejected with error `E1106`
("There are duplicate translation record...") on all tested versions. The
duplicates this tool targets are **legacy data** (created before the
validation existed, or via direct DB writes). Test data therefore has to be
seeded at the database level (`tests/seed_duplicates.py`).

#### N2. Fully identical duplicate records are invisible to the app

DHIS2 hydrates translations into a `Set` on read: two records with identical
(locale, property, value) in the database are served as **one** by the API
(verified on 2.40: both rows present in the `dataelement.translations` jsonb,
API returns one). They self-heal on any save of the object and can never
appear in this app — only duplicates with *differing* values are actionable.

## Claims investigated and rejected

- **Claim**: `engine.mutate({type: 'update'})` sends `PATCH` with
  `application/json`, which DHIS2 rejects (415) — "every fix fails on
  2.40–2.43".
- **Source**: adversarial-review subagent (cited
  `queryToRequestOptions.js: case 'update': return 'PATCH'`).
- **Refuted by**: `@dhis2/app-service-data` `DataEngine.js:58` runs
  `getMutationFetchType()` first, which maps non-partial `'update'` →
  `'replace'` → `PUT` (`getMutationFetchType.js`). Confirmed live: the e2e
  "fix selected" step succeeds and the API afterwards shows exactly one
  translation per pair with the chosen value kept (2.40 run, step "API state
  after fix": PASS).

## Architecture assessment

Migration to the App Platform was the right call for this tool and is now
done: it needed the DHIS2 header bar (previously hand-rolled and
version-sniffed), benefits from `@dhis2/ui` consistency, i18n, and
`app-runtime`'s auth/version handling, and the hand-rolled fetch layer was
the source of real quirks (silent skips, no error surfacing). The app remains
a single-view tool: no sidebar; react-router is included per platform
convention (hash router + global-shell URL sync) with a single route.

One deliberate behavior change: selection is now **per duplicate row**
(locale/property pair) instead of per object. Finer-grained, and the fix
logic still groups rows of the same object into a single PUT.

## Environment gaps

- **Laos on 2.40 not testable**: the only Laos seed is a v41 database;
  DHIS2 does not support downgrades. Laos was tested on 2.41 (native seed)
  and on 2.42/2.43 via broker in-place upgrades (Flyway migration), which
  also exercised the upgrade path.
- Everything else (broker, Playwright, DB access) was available.
