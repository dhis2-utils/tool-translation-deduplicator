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

export const duplicateGroupKey = (group: DuplicateGroup): string =>
    `${group.objectType}|${group.objectId}|${group.locale}|${group.property}`

export const translationKey = (t: Pick<Translation, 'locale' | 'property'>) =>
    `${t.locale}|${t.property}`
