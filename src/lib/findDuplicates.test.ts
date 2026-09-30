import {
    buildDuplicateGroups,
    findDuplicateTranslations,
} from './findDuplicates'

describe('findDuplicateTranslations', () => {
    it('returns empty for unique locale/property pairs', () => {
        expect(
            findDuplicateTranslations([
                { locale: 'fr', property: 'NAME', value: 'a' },
                { locale: 'fr', property: 'SHORT_NAME', value: 'b' },
                { locale: 'pt', property: 'NAME', value: 'c' },
            ])
        ).toEqual([])
    })

    it('groups duplicates by locale and property', () => {
        const duplicates = findDuplicateTranslations([
            { locale: 'fr', property: 'NAME', value: 'a' },
            { locale: 'fr', property: 'NAME', value: 'b' },
            { locale: 'pt', property: 'NAME', value: 'c' },
        ])
        expect(duplicates).toHaveLength(1)
        expect(duplicates[0].map((t) => t.value)).toEqual(['a', 'b'])
    })

    it('detects duplicates with identical values', () => {
        const duplicates = findDuplicateTranslations([
            { locale: 'fr', property: 'NAME', value: 'same' },
            { locale: 'fr', property: 'NAME', value: 'same' },
        ])
        expect(duplicates).toHaveLength(1)
        expect(duplicates[0]).toHaveLength(2)
    })
})

describe('buildDuplicateGroups', () => {
    it('builds one group per duplicated locale/property pair per object', () => {
        const groups = buildDuplicateGroups('dataElements', [
            {
                id: 'abcdefghij1',
                displayName: 'DE 1',
                translations: [
                    { locale: 'fr', property: 'NAME', value: 'x' },
                    { locale: 'fr', property: 'NAME', value: 'y' },
                    { locale: 'lo', property: 'SHORT_NAME', value: 'z' },
                    { locale: 'lo', property: 'SHORT_NAME', value: 'z' },
                ],
            },
            {
                id: 'abcdefghij2',
                displayName: 'DE 2',
                translations: [{ locale: 'fr', property: 'NAME', value: 'x' }],
            },
            { id: 'abcdefghij3' },
        ])
        expect(groups).toHaveLength(2)
        expect(groups[0]).toMatchObject({
            objectType: 'dataElements',
            objectId: 'abcdefghij1',
            locale: 'fr',
            property: 'NAME',
            values: ['x', 'y'],
        })
        expect(groups[1]).toMatchObject({
            locale: 'lo',
            property: 'SHORT_NAME',
            values: ['z', 'z'],
        })
    })
})
