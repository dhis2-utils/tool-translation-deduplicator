# End-to-end tests

Playwright-based e2e suite for the Translation Deduplicator app.

**WARNING: the suite mutates metadata (adds and removes translations). Only
run it against disposable test instances.**

## Prerequisites

- Python 3 with `playwright` installed (`pip install playwright && playwright install chromium`)
- The app installed on the target instance (`pnpm build`, then upload
  `build/bundle/*.zip` via App Management or `POST /api/apps`)

## Running

```bash
export DHIS2_URL=http://localhost:8080   # target instance
export DHIS2_USER=admin
export DHIS2_PASS=district
export LABEL=2.42-sl                     # used for the output folder

# 1. Seed known duplicate translations and write the manifest
python3 tests/seed_duplicates.py seed-manifest.json

# 2. Run the suite
SEED_MANIFEST=seed-manifest.json python3 tests/e2e/test_dedup_app.py
```

Results and screenshots land in `tests/e2e/output/<LABEL>/`.

The suite is frame-aware: it finds the app both when served top-level
(DHIS2 ≤ 2.41) and inside the global-shell iframe (2.42+).
