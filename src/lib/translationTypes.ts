export interface Translation {
    locale: string
    property: string
    value: string
}

export interface TranslatableSchema {
    plural: string
    translatable: boolean
    relativeApiEndpoint?: string
}

export interface TranslatedObject {
    id: string
    displayName?: string
    translations?: Translation[]
}

/**
 * One duplicate group: a single object having more than one translation
 * for the same (locale, property) pair. `values` holds the candidate
 * translation values in the order they appear on the object.
 */
export interface DuplicateGroup {
    objectType: string
    objectId: string
    objectName: string
    locale: string
    property: string
    values: string[]
}

/**
 * Object types whose duplicate translations cannot be fixed through the
 * Web API (verified on DHIS2 2.40–2.43):
 * - categoryOptionCombos: PUT returns 200 OK but the importer silently
 *   ignores the update (and the response carries no import report to
 *   detect it) — the duplicate reappears on rescan.
 * - maps: the GET `fields=:owner` + PUT round-trip re-inserts the
 *   embedded mapViews and fails with a 409 unique-constraint violation.
 * Duplicates on these types require database-level cleanup.
 */
export const UNFIXABLE_TYPES: ReadonlySet<string> = new Set([
    'categoryOptionCombos',
    'maps',
])

export const duplicateGroupKey = (group: DuplicateGroup): string =>
    `${group.objectType}|${group.objectId}|${group.locale}|${group.property}`

export const translationKey = (t: Pick<Translation, 'locale' | 'property'>) =>
    `${t.locale}|${t.property}`
