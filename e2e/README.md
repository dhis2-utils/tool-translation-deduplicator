> [!WARNING]
> This suite creates, changes and deletes metadata and users, and installs and uninstalls the app. Run it only against a throwaway DHIS2 instance that you can reset or recreate, never against a play, shared test or production server.

# End-to-end tests

A Playwright for Python suite that drives the built Translation Deduplication Tool on a live DHIS2 instance. It follows the `e2e/run.sh` contract, version 1, from [TESTING.md](https://github.com/dhis2-utils/reference-tool-conventions/blob/main/TESTING.md) in reference-tool-conventions.

## Get a throwaway instance

Start a local DHIS2 instance in Docker, as described in [DHIS2 in Docker](https://developers.dhis2.org/docs/tutorials/dhis2-docker/). The suite works on an empty database and on a demo database. It does not need database access.

## Install the dependencies

```bash
pip install -r e2e/requirements.txt
playwright install chromium
```

## Run the suite

```bash
pnpm build
mkdir -p /tmp/e2e-results
DHIS2_URL=http://localhost:8080 DHIS2_USER=<user> DHIS2_PASS=<password> \
APP_ZIP=$PWD/build/bundle/tool-translation-deduplicator-<version>.zip \
RESULTS_DIR=/tmp/e2e-results e2e/run.sh
```

| Variable                   | Required | Meaning                                                          |
| -------------------------- | -------- | ---------------------------------------------------------------- |
| `DHIS2_URL`                | yes      | Instance base URL, no trailing slash                             |
| `DHIS2_USER`, `DHIS2_PASS` | yes      | A user with the `ALL` authority                                  |
| `APP_ZIP`                  | yes      | Absolute path of the built bundle                                |
| `RESULTS_DIR`              | yes      | Existing directory for `results.json`, screenshots and `run.log` |
| `LABEL`                    | no       | Label for the output. Default: the server version                |
| `APP_KEY`                  | no       | Default: the key that the server gives the installed app         |
| `SCAN_TIMEOUT_MS`          | no       | How long to wait for a scan. Default: 600000                     |
| `FIX_TIMEOUT_MS`           | no       | How long to wait for a fix to finish. Default: 600000            |

Exit codes: `0` when every test passed, `1` when a test failed, `2` when the suite could not run. On `2`, `results.json` has an `error` field that names the stage that failed.

## What the suite does

1. Installs `APP_ZIP` and finds the key that the server gave it.
2. Deletes what an earlier, interrupted run left behind, from the record in the dataStore at `e2e-state/tool-translation-deduplicator`.
3. Seeds its own objects, each named `E2E tool-translation-deduplicator <run id> ...`, and records them in the dataStore before it creates them: three data elements, a data set, an option set with one option, a category model, a map and a user with only the app authority. Since DHIS2 2.40 a normal save rejects duplicate translations, so the suite imports them with `skipValidation=true`, then reads them back.
4. Runs the tests in the following list.
5. Deletes the seeded objects and the record, and uninstalls the app.

| Test id                    | Checks                                                                                   |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| `app-loads`                | The app opens, at the top level (2.41 and earlier) or in the global-shell iframe (2.42+) |
| `scan-completes`           | The scan finishes                                                                        |
| `seeded-rows-listed`       | Every seeded duplicate has a row                                                         |
| `html-shown-as-text`       | A translation that contains HTML is shown as text and its script does not run            |
| `unfixable-flagged`        | Map and category option combination rows have the tag and no checkbox                    |
| `select-all-toggles`       | The header checkbox chooses every fixable object and clears them again                   |
| `object-selected-as-whole` | One checkbox chooses all rows of its object                                              |
| `choose-value`             | A value other than the first can be chosen                                               |
| `fix-single-object`        | Fixing one object with two duplicate pairs succeeds                                      |
| `permission-refused`       | A user without write sharing gets an error that names the object, and nothing changes    |
| `fix-seeded-objects`       | Fixing the other seeded objects succeeds                                                 |
| `api-state`                | The API shows one value per pair, the chosen value, and untouched unfixable objects      |
| `owner-fields-unchanged`   | No field other than translations and audit fields changed on the fixed objects           |
| `rescan-clean`             | A new scan no longer lists the fixed objects                                             |
| `no-page-errors`           | No page errors and no failed requests                                                    |
| `cleanup`                  | Every seeded object was deleted                                                          |

The suite never fixes duplicates it did not seed, so it leaves real duplicates on a demo database as they are.
