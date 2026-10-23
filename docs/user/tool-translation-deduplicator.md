# Translation Deduplication Tool { #tool-translation-deduplicator-guide }

## What the tool is for { #tool-translation-deduplicator-about }

The Translation Deduplication Tool finds metadata objects that have more than one translation for the same locale and property, and removes the extra translations. It is for system administrators who clean up metadata.

A _duplicate translation_ is a second translation of the same property in the same locale on one object. For example, a data element with two different French translations of its name. DHIS2 2.40 and later refuse to save such duplicates, so the duplicates that the tool finds are old data. They come from versions before that check, or from changes made directly in the database. An object with a duplicate translation cannot be saved in other apps, such as the Maintenance app, until the duplicate is removed.

## Before you start { #tool-translation-deduplicator-before-you-start }

The tool supports DHIS2 2.40 and later.

To open the tool, you need the `ALL` authority, or a user role that includes the tool's app authority. In the user role editor of the Users app, the app authority is called **tooltranslationdeduplicator app**.

To fix a duplicate, you also need write sharing on the object. The tool only finds duplicates on objects that you can read. To check all metadata, use an account that can read all metadata.

> **Warning**
>
> The tool deletes the translations that you do not keep, and it has no undo. Make a backup of the database before you fix duplicates. Try the tool on a copy of the database first.

## Install the tool { #tool-translation-deduplicator-install }

You can install the tool in two ways. The tool is not on the App Hub.

To install the tool from its GitHub release:

1. Download `tool-translation-deduplicator-<version>.zip` from the [releases page of the tool](https://github.com/dhis2-utils/tool-translation-deduplicator/releases/latest).
2. Open the App Management app.
3. Click **Manual install**.
4. Click **Upload an app to install**, and choose the zip file.

The tool appears in the apps menu as **Translation Deduplication Tool**.

You can also install the tool from the DHIS2 Admin Toolbox app, if the toolbox is installed on your instance.

<!-- VERIFY IN APP: the tool is listed in the DHIS2 Admin Toolbox (tool-box tools.json). -->

## Find duplicate translations { #tool-translation-deduplicator-find }

The tool scans all translatable metadata when you open it.

1. Open the **Translation Deduplication Tool** from the apps menu.
2. Wait for the scan to finish. A progress bar shows how far the scan is. On a large database, the scan can take several minutes.

If the tool finds no duplicates, it shows **No duplicate translations found**.

If the tool finds duplicates, it lists them in the **Duplicate translations** table. The table has one row for each locale and property that has duplicates. The rows of one object are grouped together and share one checkbox.

| Column                  | Content                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| **Object type**         | The type of the object, as the API names it, for example `dataElements` or `indicators`.   |
| **ID**                  | The UID of the object.                                                                     |
| **Name**                | The name of the object.                                                                    |
| **Locale**              | The locale of the duplicate translations.                                                  |
| **Property**            | The translated property, for example `NAME` or `SHORT_NAME`.                               |
| **Translation to keep** | The different values. You choose the value to keep here. The tool chooses the first value. |

If the tool cannot read an object type, it shows **Some object types could not be checked** and lists the types. Usually the cause is missing access. The results do not include these types.

To scan again, for example after a change in another app, click **Rescan**.

## Fix duplicate translations { #tool-translation-deduplicator-fix }

When you fix an object, the tool keeps one value for each locale and property, and deletes the other values.

> **Warning**
>
> The tool deletes the values that you do not keep. You cannot undo a fix in the tool.

1. In the **Translation to keep** column, choose the value to keep for each row.
2. Choose the checkbox of each object that you want to fix. The checkbox in the table header chooses all objects that the tool can fix.
3. Click **Fix selected**. The button shows the number of rows that you chose.

The tool updates the objects one at a time. With many objects, this can take several minutes. When the tool finishes, it shows a message with the number of fixed rows. The fixed objects disappear from the table.

A checkbox chooses all rows of its object, because DHIS2 only accepts the update when all the object's duplicates are fixed together.

If an update fails, the tool shows **Some updates failed**. The list gives the name and UID of each object, and the reason from the server. The rows stay in the table. A common reason is that you do not have write sharing on the object.

## Known limitations { #tool-translation-deduplicator-limitations }

- **Maps and category option combinations.** The tool cannot fix duplicates on maps or category option combinations. It lists them with the tag **Cannot be fixed via API**, without a checkbox. DHIS2 rejects the update for maps. For category option combinations, DHIS2 returns success but does not save the change. You must remove these duplicates in the database.
- **Identical duplicates.** The tool cannot find two translations with the same locale, property and value. The API returns them as one translation. DHIS2 removes the extra copy the next time the object is saved.
- **Access.** The tool only checks the object types and objects that you can read, and only fixes the objects that you can write.
- **Load on the server.** The scan reads every object of every translatable type in one request per type. On a large database, this takes time and memory on the server. Run the scan outside busy hours.
- **Version number of objects.** Each fix saves the whole object, so DHIS2 increases the version number of objects that have one, such as data sets and programs. Android devices then download the metadata of those objects again.
- **No sorting or paging.** The table lists every duplicate in one long list, in the order the tool found them.
