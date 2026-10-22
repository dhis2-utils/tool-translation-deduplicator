# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- the user documentation moved from `MANUAL.md` to `docs/user/`, in the docs.dhis2.org format, and now names the app authority and the sharing that a fix needs
- the e2e suite moved to `e2e/` and follows the `e2e/run.sh` contract: it seeds its own objects through the API, cleans up after itself and writes `results.json`
- the CI and release workflows match the current templates (read-only CI token, no dependency cache in the release job, re-runnable release step)
- the app description no longer repeats the word "tool"
- linting and formatting moved from ESLint and Prettier to Ultracite on Oxlint and Oxfmt, with the DHIS2 house style (shared lint templates)

### Security

- updated `react-router-dom` to 6.30.6 (GHSA-jjmj-jmhj-qwj2; the app has one route and was not exploitable)

## [1.0.0] - 2026-09-30

### Changed

- migrated from the vanilla webpack/materialize toolchain to the DHIS2 App Platform (React, TypeScript, `@dhis2/app-runtime`, `@dhis2/ui`)
- header bar is now provided by the platform on all supported versions (2.40+), including the global app shell on 2.42+
- selection works per object (all of an object's duplicate rows are fixed together, because DHIS2 rejects updates of objects that still contain duplicates)
- failed updates are now listed per object with the server's error message
- object types that DHIS2 cannot update through the API (`maps`, `categoryOptionCombos`) are flagged "Cannot be fixed via API" instead of being selectable (fixing them silently failed or was rejected; they need database-level cleanup)
- object types that cannot be checked (for example because of missing access) are now reported in the UI instead of being silently skipped
- added unit tests for the duplicate-detection logic and a Playwright e2e suite
- the app is now consistently called "Translation Deduplication Tool" (it was "Translation Deduplicator Tool" in the header bar and three other names in the docs)
- the user manual is updated for this version

### Fixed

- choosing between two identical duplicate values could re-introduce both values on save

## [0.2.0] - 2025-09-05

### Added

- support for the global app shell (header bar) in DHIS2 2.42 and later

### Fixed

- not all translatable metadata was checked
