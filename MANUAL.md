### User Manual for the Translation Deduplication Tool

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Using the App](#using-the-app)
    - [Overview](#overview)
    - [Navigating the UI](#navigating-the-ui)
    - [Types that cannot be fixed via the API](#types-that-cannot-be-fixed-via-the-api)
4. [Warnings](#warnings)

## Introduction

The DHIS2 Translation Deduplication Tool allows users to identify and fix duplicate translation entries within the DHIS2 platform. This helps maintain clean and consistent translation data across the system, and prevents problems with import and editing of affected metadata.

A duplicate means that a single metadata object holds more than one translation for the same locale and property — for example a data element with two different French `NAME` translations. Since DHIS2 2.40 the API rejects attempts to create such duplicates, so what this tool finds is legacy data: translations created before that validation existed, or written directly to the database.

Two translation records that are _completely_ identical (same locale, property and value) are served as one by the API and can therefore never show up in this app. Only duplicates with differing values are actionable — and they are the ones that cause problems.

The app is built on the DHIS2 App Platform and supports DHIS2 2.40 and later.

## Installation

To install the app, follow these steps:

1. **Download the App Archive**:
    - Obtain the `.zip` file for the tool

2. **Access DHIS2 App Management**:
    - Log in to your DHIS2 instance with administrative privileges.
    - Navigate to the "App Management" section through the main menu.

3. **Upload the App**:
    - In the "App Management" section, click on the "Install app" button.
    - Select and upload the `.zip` file you downloaded earlier.
    - Follow the prompts to complete the installation.

4. **Verify Installation**:
    - Once installed, ensure the app appears in the list of available apps.
    - Unless the user has the `ALL` authority, the app must be added to the appropriate user role
    - You can now launch the app from the DHIS2 dashboard.

## Using the App

### Overview

The Translation Deduplication Tool provides a user-friendly interface to detect and resolve duplicate translations. Below is a guide to navigating the app and using its features effectively.

### Navigating the UI

1. **Launch the App**:
    - From the DHIS2 apps menu, open "Translation Deduplication Tool".

2. **Scanning for duplicates**:
    - The scan starts automatically when the app opens: it looks up every translatable object type, then reads all objects of each type and compares their translations.
    - A progress bar shows how far the scan has got. On large instances it reads a lot of metadata and can take a while.
    - If a type cannot be read — most often because the user lacks access to it — the app finishes the scan and reports it in a "Some object types could not be checked" notice, listing the types that were skipped. Those types are simply not covered by the results.

3. **Reviewing Duplicates**:
    - When the scan finishes, the duplicates found are listed in a table.
    - There is one row per locale and property that has duplicate translations. If an object has duplicates for several locale/property pairs, its rows are grouped together and share a single checkbox and one set of object cells.
    - If nothing is found, the app shows a "No duplicate translations found" message instead of the table.

4. **Table Columns**:
    - **(checkbox)**: The first column selects an object for fixing. There is one checkbox per object, not per row.
    - **Object type**: The metadata type as named in the API (for example `dataElements`, `indicators`, `organisationUnits`).
    - **ID**: Unique identifier of the object.
    - **Name**: Name of the object.
    - **Locale**: Language locale of the duplicate translations.
    - **Property**: The translated property (for example `NAME`, `SHORT_NAME`, `DESCRIPTION`).
    - **Translation to keep**: The duplicate values, with a radio button to choose which one to keep. The first value is preselected.

5. **Selecting objects to fix**:
    - Selection works per object: ticking a checkbox selects all of that object's duplicate rows. The fix rewrites the whole object, and DHIS2 only accepts the update once _all_ of the object's duplicates are resolved, so they have to be fixed together.
    - The checkbox in the table header selects every object that can be fixed, skipping the types described below. It shows a partial state when only some objects are selected.

6. **Choosing which translation to keep**:
    - For each locale/property row, pick the value to keep with the radio buttons. The other values for that locale and property are discarded when the fix is applied.
    - If the duplicate values are identical, either one can be kept — the result is the same.

7. **Fix Selected Translations**:
    - Click "Fix selected", which shows the number of objects currently selected.
    - The app updates the selected objects one at a time, so fixing many objects can take several minutes. The button shows a spinner while the run is in progress.
    - Use the "Rescan" button to re-check the instance at any time — for example after fixing, or to pick up changes made elsewhere.

8. **Results**:
    - Objects that were updated successfully disappear from the table.
    - If an update fails, the app shows a "Some updates failed" notice listing each object that could not be updated, with its name, ID and the error message returned by the server. The rows stay in the table so the failures can be retried or investigated.
    - The table is not otherwise refreshed from the server; use "Rescan" for an up-to-date picture.

### Types that cannot be fixed via the API

Duplicates on some object types cannot be repaired through the DHIS2 API at all — currently `maps` and `categoryOptionCombos`. For maps, the update is rejected by the database; for category option combos the server accepts the update but silently ignores it, so the duplicate would simply come back on the next scan.

These duplicates are still listed, so they are visible, but they are tagged "Cannot be fixed via API", their values are shown without radio buttons, and they cannot be selected — including by the select-all checkbox. Resolving them requires cleaning up the data directly in the database.

## Warnings

1. **Use in Development/Test Environment**:
    - It is recommended to use and test this app in a **development or test environment**. This will prevent unintended modifications in the production environment.

2. **Fixes cannot be undone**:
    - Applying a fix deletes the duplicate translations that were not chosen. There is no undo in the app, so make sure a backup exists before fixing duplicates in a production database.

3. **Metadata Access**:
    - The app operates based on the metadata a user has access to. For a comprehensive deduplication review, ensure the user has access to **all metadata**. Incomplete access may lead to partial operation and inconsistent results.

4. **User Permissions**:
    - Ensure the user has sufficient permissions to modify translations in DHIS2. Lack of permissions can result in operation failures.

5. **Large instances take time**:
    - The scan reads all translatable metadata, and fixes are applied one object at a time. On a large database both steps can take minutes. Leave the app open while they run.
