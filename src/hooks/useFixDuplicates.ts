import { useAlert, useDataEngine } from '@dhis2/app-runtime'
import i18n from '@dhis2/d2-i18n'
import { useMutation } from '@tanstack/react-query'
import {
    DuplicateGroup,
    Translation,
    duplicateGroupKey,
    translationKey,
} from '../lib/translationTypes'

export interface FixSelection {
    group: DuplicateGroup
    /** The translation value to keep for this (locale, property) pair */
    selectedValue: string
}

export interface FailedObject {
    objectId: string
    objectName: string
    message: string
}

export interface FixResult {
    fixedKeys: Set<string>
    failedKeys: Set<string>
    failedObjects: FailedObject[]
}

interface OwnedObject {
    translations?: Translation[]
    [property: string]: unknown
}

/**
 * Pull the human-readable validation messages (e.g. E1106) out of an
 * app-runtime FetchError; fall back to the generic error message.
 */
const extractErrorMessage = (error: unknown): string => {
    const details = (
        error as {
            details?: {
                response?: { errorReports?: { message?: string }[] }
            }
        }
    ).details
    const reports = details?.response?.errorReports
        ?.map((report) => report.message)
        .filter(Boolean)
    if (reports?.length) {
        return reports.join('; ')
    }
    return error instanceof Error ? error.message : String(error)
}

/**
 * Applies the chosen fixes: for every affected object, fetch the full
 * (owned) object, drop all translations belonging to the selected
 * duplicate groups, re-add the single chosen value per group, and PUT
 * the object back. Objects are updated one at a time; one failing
 * object does not block the others.
 */
export const useFixDuplicates = ({
    onComplete,
}: {
    onComplete: (result: FixResult) => void
}) => {
    const engine = useDataEngine()

    const { show: showResultAlert } = useAlert(
        ({ fixed, failed }: { fixed: number; failed: number }) =>
            failed === 0
                ? i18n.t('Fixed {{fixed}} duplicate translation issue(s)', {
                      fixed,
                  })
                : i18n.t(
                      'Fixed {{fixed}} issue(s), {{failed}} update(s) failed',
                      { fixed, failed }
                  ),
        ({ failed }: { failed: number }) =>
            failed === 0 ? { success: true } : { critical: true }
    )

    const mutation = useMutation<FixResult, Error, FixSelection[]>(
        async (selections: FixSelection[]) => {
            const byObject = new Map<string, FixSelection[]>()
            for (const selection of selections) {
                const objectKey = `${selection.group.objectType}|${selection.group.objectId}`
                const existing = byObject.get(objectKey)
                if (existing) {
                    existing.push(selection)
                } else {
                    byObject.set(objectKey, [selection])
                }
            }

            const result: FixResult = {
                fixedKeys: new Set(),
                failedKeys: new Set(),
                failedObjects: [],
            }

            for (const objectSelections of byObject.values()) {
                const { objectType, objectId } = objectSelections[0].group
                try {
                    const response = (await engine.query({
                        object: {
                            resource: objectType,
                            id: objectId,
                            params: { fields: ':owner' },
                        },
                    })) as { object: OwnedObject }
                    const object = response.object

                    const selectedKeys = new Set(
                        objectSelections.map((s) => translationKey(s.group))
                    )
                    const keptTranslations = (object.translations ?? []).filter(
                        (t) => !selectedKeys.has(translationKey(t))
                    )
                    for (const selection of objectSelections) {
                        keptTranslations.push({
                            locale: selection.group.locale,
                            property: selection.group.property,
                            value: selection.selectedValue,
                        })
                    }

                    await engine.mutate({
                        resource: objectType,
                        id: objectId,
                        type: 'update',
                        data: { ...object, translations: keptTranslations },
                    })

                    for (const selection of objectSelections) {
                        result.fixedKeys.add(duplicateGroupKey(selection.group))
                    }
                } catch (error) {
                    console.error(
                        `Failed to update ${objectType}/${objectId}:`,
                        error
                    )
                    for (const selection of objectSelections) {
                        result.failedKeys.add(
                            duplicateGroupKey(selection.group)
                        )
                    }
                    result.failedObjects.push({
                        objectId,
                        objectName: objectSelections[0].group.objectName,
                        message: extractErrorMessage(error),
                    })
                }
            }

            return result
        },
        {
            onSuccess: (result) => {
                showResultAlert({
                    fixed: result.fixedKeys.size,
                    failed: result.failedKeys.size,
                })
                onComplete(result)
            },
        }
    )

    return {
        fixDuplicates: mutation.mutate,
        isFixing: mutation.isLoading,
    }
}
