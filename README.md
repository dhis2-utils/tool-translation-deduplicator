# Translation Deduplication Tool

> ![Maturity: Validated](https://img.shields.io/badge/maturity-Validated-yellow)  
> Intended use: remove duplicate translations from metadata objects (one object having multiple translations for the same locale and property).  
> Maintainers: HISP Centre implementation team.

> [!WARNING]
> This tool is for system administrators doing specific clean-up tasks, not for end users. It is a DHIS2 app, but it has not been through the same testing as the core apps. It deletes translations and has no undo: back up the database first, and try the tool on a test instance.

A DHIS2 app that finds metadata objects with more than one translation for the same locale and property, and keeps the one you choose. The user documentation is in [`docs/user/`](docs/user/tool-translation-deduplicator.md), and its [known limitations](docs/user/tool-translation-deduplicator.md#tool-translation-deduplicator-limitations) section lists what the tool cannot do.

## Supported DHIS2 versions

2.40 and later (`minDHIS2Version` in `d2.config.js`). The e2e suite is run on the last three DHIS2 majors and on 2.40.

## Development

This is a [DHIS2 App Platform](https://developers.dhis2.org/docs/app-platform/getting-started) app (React and TypeScript).

### Prerequisites

- Node.js 22.
- pnpm, in the version set by `packageManager` in `package.json`. With Corepack enabled (`corepack enable`), pnpm picks that version up.
- A DHIS2 instance to run against, for example a local one in Docker: see [DHIS2 in Docker](https://developers.dhis2.org/docs/tutorials/dhis2-docker/).

### Install dependencies

```bash
pnpm install
```

### Start against a local instance

```bash
pnpm start --proxy http://localhost:8080
```

The app starts on http://localhost:3000. The proxy forwards API requests to the DHIS2 instance, and you log in through the app.

### Test, lint and build

```bash
pnpm test        # unit tests (src/**/*.test.ts)
pnpm lint        # Ultracite on Oxlint and Oxfmt, over the DHIS2 house style
pnpm fix         # apply the safe fixes
pnpm exec tsc --noEmit
pnpm build       # writes build/bundle/tool-translation-deduplicator-<version>.zip
```

Linting follows the [shared lint setup](https://github.com/dhis2-utils/reference-tool-conventions/blob/main/LINTING.md); `AGENTS.md` has the rules for coding agents. The end-to-end suite drives the built app on a live DHIS2 instance. It changes and deletes data, so run it only on a throwaway instance. See [`e2e/README.md`](e2e/README.md).

### Release

Releases follow the [shared release workflow](https://github.com/dhis2-utils/reference-tool-conventions/blob/main/RELEASE-WORKFLOW.md): bump `version` in `package.json`, add a `## [x.y.z]` section to `CHANGELOG.md`, merge to `main`, then push a `vx.y.z` tag from `main`. The release workflow builds the app and attaches the zip to a GitHub release.

## License

BSD-3-Clause, see [LICENSE](LICENSE). © University of Oslo.
