### User Manual for Translation Duplicator Tool

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Using the App](#using-the-app)
    - [Overview](#overview)
    - [Navigating the UI](#navigating-the-ui)
4. [Warnings](#warnings)

## Introduction
The DHIS2 Translation Duplicator Tool allows users to identify and fix duplicate translation entries within the DHIS2 platform. This helps maintain clean and consistent translation data across the system, and prevents problems with import and editing of affected metadata.

## Installation
To install the DHIS2 Translation Duplicate Fix Web App, follow these steps:

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
   - Unless the user has the `ALL` authority, the app must be added to the approprite user role
   - You can now launch the app from the DHIS2 dashboard.

## Using the App

### Overview
The Translation Duplicator Tool provides a user-friendly interface to detect and resolve duplicate translations. Below is a guide to navigating the app and using its features effectively.

### Navigating the UI
1. **Launch the App**:
   - From the DHIS2 dashboard, click on the app's icon to open the DHIS2 Translation Duplicate Fix Web App.

2. **Loading Metadata**:
   - Upon launching, the app will automatically start loading metadata elements and identifying duplicate translations.
   - A progress bar will display the loading status.

3. **Reviewing Duplicates**:
   - Once the metadata is loaded, you will see a table listing duplicates.
   - Each row corresponds to a duplicate entry for a translation.

4. **Table Columns**:
   - **Select**: Checkbox to select individual rows for fixing. Each row is one locale/property pair with duplicate translations, and can be fixed independently.
   - **Object Type**: Type of DHIS2 object (e.g., data element, organization unit).
   - **ID**: Unique identifier of the object.
   - **Name**: Name of the object.
   - **Locale**: Language locale for the translation.
   - **Property**: The property of the object being translated (e.g., name, description).
   - **Translation to keep**: List of duplicate translations with radio buttons to select the preferred translation to keep

5. **Select All/Deselect All**:
   - At the top left of the table, there is a "Select All" checkbox.
   - Checking this will select all rows in the table.
   - Unchecking it will deselect all rows.

6. **Fix Selected Translations**:
   - After reviewing the duplicates and selecting rows to fix, click the "Fix selected" button located above the table.
   - The app will process the selected rows and update translations to remove duplicates.
   - A notification will inform you of the success or failure of the operation.
   - Use the "Rescan" button to re-check the instance at any time.

7. **Feedback**:
   - Success and failure messages will be displayed
   - The table will refresh to reflect updated translations

## Warnings
1. **Use in Development/Test Environment**:
   - It is recommended to use and test this app in a **development or test environment**. This will prevent unintended modifications in the production environment.

2. **Metadata Access**:
   - The app operates based on the metadata a user has access to. For a comprehensive deduplication review, ensure the user has access to **all metadata**. Incomplete access may lead to partial operation and inconsistent results.

3. **User Permissions**:
   - Ensure the user has sufficient permissions to modify translations in DHIS2. Lack of permissions can result in operation failures.
