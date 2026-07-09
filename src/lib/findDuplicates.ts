import {
    DuplicateGroup,
    Translation,
    TranslatedObject,
    translationKey,
} from './translationTypes'

/**
 * Group an object's translations by (locale, property) and return the
 * groups that contain more than one entry — i.e. duplicates.
 */
export const findDuplicateTranslations = (
    translations: Translation[]
): Translation[][] => {
    const byKey = new Map<string, Translation[]>()
    for (const translation of translations) {
        const key = translationKey(translation)
        const group = byKey.get(key)
        if (group) {
            group.push(translation)
        } else {
            byKey.set(key, [translation])
        }
    }
    return [...byKey.values()].filter((group) => group.length > 1)
}

/**
 * Build the flat list of duplicate groups for all objects of one type.
 */
export const buildDuplicateGroups = (
    objectType: string,
    objects: TranslatedObject[]
): DuplicateGroup[] => {
    const groups: DuplicateGroup[] = []
    for (const object of objects) {
        if (!object.translations?.length) {
            continue
        }
        for (const duplicates of findDuplicateTranslations(
            object.translations
        )) {
            groups.push({
                objectType,
                objectId: object.id,
                objectName: object.displayName ?? object.id,
                locale: duplicates[0].locale,
                property: duplicates[0].property,
                values: duplicates.map((t) => t.value),
            })
        }
    }
    return groups
}
