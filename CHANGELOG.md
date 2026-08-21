# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0]

- migrated from the vanilla webpack/materialize toolchain to the DHIS2 App Platform (React, TypeScript, `@dhis2/app-runtime`, `@dhis2/ui`)
- header bar is now provided by the platform on all supported versions (2.40+), including the global app shell on 2.42+
- selection works per object (all of an object's duplicate rows are fixed together — DHIS2 rejects updates of objects that still contain duplicates)
- failed updates are now listed per object with the server's error message
- object types that DHIS2 cannot update through the API (`maps`, `categoryOptionCombos`) are flagged "Cannot be fixed via API" instead of being selectable (fixing them silently failed or was rejected; they need database-level cleanup)
- fixed: choosing between two identical duplicate values could re-introduce both values on save
- object types that cannot be checked (e.g. no access) are now reported in the UI instead of being silently skipped
- added unit tests for the duplicate-detection logic and a Playwright e2e suite
- the app is now consistently called "Translation Deduplication Tool" (it was "Translation Deduplicator Tool" in the header bar and three other names in the docs)
- the user manual is updated for this version

## [0.2.0]

- added support for global app shell (header bar) in DHIS2 42+
- fixed bug that prevented all translateable metadata to be checked
