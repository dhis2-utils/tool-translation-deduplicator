# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0]

- migrated from the vanilla webpack/materialize toolchain to the DHIS2 App Platform (React, TypeScript, `@dhis2/app-runtime`, `@dhis2/ui`)
- header bar is now provided by the platform on all supported versions (2.40+), including the global app shell on 2.42+
- duplicates can now be selected and fixed per locale/property row instead of per object
- fixed: choosing between two identical duplicate values could re-introduce both values on save
- object types that cannot be checked (e.g. no access) are now reported in the UI instead of being silently skipped
- added unit tests for the duplicate-detection logic and a Playwright e2e suite

## [0.2.0]

- added support for global app shell (header bar) in DHIS2 42+
- fixed bug that prevented all translateable metadata to be checked