# State changes: Translation Deduplication Tool review, 2026-07-09

Every persistent change made during this review, and its disposition.

## Project files

| File                                                   | Change                                                          | Disposition                                       |
| ------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------- |
| entire repo                                            | migrated to App Platform on branch `app-platform-migration`     | committed on the branch; not pushed (user pushes) |
| `d2auth.json`                                          | **not touched** (obsolete under the platform; still gitignored) | left in place                                     |
| `tests/`, `docs/review-2026-07-09-platform-migration/` | new test suite + review artefacts                               | committed                                         |

## DHIS2 instances (broker)

| Instance        | Version                                    | Seed                                | Disposition                      |
| --------------- | ------------------------------------------ | ----------------------------------- | -------------------------------- |
| `agent-td40`    | 2.40.12                                    | sierra-leone V40                    | deleted after testing            |
| `agent-td41`    | 2.41.9                                     | sierra-leone v41                    | deleted after testing            |
| `agent-td42`    | 2.42.5.1                                   | sierra-leone v42                    | deleted after testing            |
| `agent-td43`    | 2.43.0.1                                   | sierra-leone v43                    | deleted after testing            |
| `agent-tdlao`   | 2.41.9                                     | lao_hmis_demo_v41                   | deleted after testing (see note) |
| `agent-tdlao42` | 2.42.5.1                                   | lao_hmis_demo_v41 (Flyway-migrated) | deleted after testing            |
| `agent-tdlao43` | 2.43.0.1                                   | lao_hmis_demo_v41 (Flyway-migrated) | deleted after testing            |
| `agent-la-dev`  | (pre-existing, not created by this review) | —                                   | **left untouched**               |

Note: an in-place WAR upgrade of `agent-tdlao` 2.41→2.42 left the instance
broken (created-at-41 instances run Tomcat 9; DHIS2 2.42+ needs Tomcat 10, so
the new WAR never deployed — everything 404s). Fresh per-version instances
with the v41 seed were used instead; Flyway migrated the DB on first boot.

The `lao_hmis_demo_v41` seed ships with the `admin` account disabled; on each
Laos instance it was re-enabled with password `district` directly in the DB
(`tests/e2e/prep_lao_admin.sh`) before testing. Instances were deleted after,
so nothing persists.

## Test data created

On every test instance: duplicate translations (locale `fr`) seeded directly
into the DB on 2 data elements, 1 indicator, 1 organisation unit
(`tests/seed_duplicates.py`). The app's own "fix" flow removed them during the
e2e run, and the instances were deleted afterwards — nothing persists.

The app zip was installed via `POST /api/apps` and the instance deleted
afterwards (no uninstall needed).

## System settings changed

None. (No CORS changes needed — the app was tested as an installed bundle,
same-origin.)

## Not reverted — action needed

Nothing. All broker instances created by this review were deleted.
