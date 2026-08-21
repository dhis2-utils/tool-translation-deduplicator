# Translation Deduplication Tool

Tool to identify and fix metadata objects with duplicate translations (one object having multiple translations for the same locale and property).

> **WARNING**
> This tool is intended to be used by system administrators to perform specific tasks, it is not intended for end users. It is available as a DHIS2 app, but has not been through the same rigorous testing as normal core apps. It should be used with care, and always tested in a development environment.

## License

© Copyright University of Oslo 2024

## Getting started

This is a [DHIS2 App Platform](https://developers.dhis2.org/docs/app-platform/getting-started) app (React + TypeScript). It supports DHIS2 2.40 and later.

### Install dependencies

```
pnpm install
```

### Start dev server

```
pnpm start --proxy https://your-dhis2-instance.example.org
```

This starts the app on http://localhost:3000 with a proxy that forwards API requests to the given DHIS2 instance (you log in through the app itself).

### Build an installable zip

```
pnpm build
```

The installable app bundle is written to `build/bundle/tool-translation-deduplicator-<version>.zip` and can be installed through the App Management app in DHIS2.

### Run tests

```
pnpm test        # unit tests
pnpm lint        # eslint + prettier
```

End-to-end Playwright tests live in `tests/e2e/` — see `tests/e2e/README.md`.
