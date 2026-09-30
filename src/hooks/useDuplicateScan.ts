import { useDataEngine } from '@dhis2/app-runtime'
import { useCallback, useEffect, useRef, useState } from 'react'
import { buildDuplicateGroups } from '../lib/findDuplicates'
import {
    DuplicateGroup,
    TranslatableSchema,
    TranslatedObject,
} from '../lib/translationTypes'
import { useTranslatableSchemas } from './useTranslatableSchemas'

export type ScanStatus = 'loading-schemas' | 'scanning' | 'done' | 'error'

export interface ScanState {
    status: ScanStatus
    /** 0–100, only meaningful while scanning */
    progress: number
    duplicates: DuplicateGroup[]
    /** object types that could not be fetched and were skipped */
    failedTypes: string[]
    error?: Error
}

const INITIAL_STATE: ScanState = {
    status: 'loading-schemas',
    progress: 0,
    duplicates: [],
    failedTypes: [],
}

/**
 * Scans every translatable object type for duplicate translations,
 * reporting progress along the way. The scan starts automatically once
 * the schemas are loaded, and can be restarted with `rescan()`.
 */
export const useDuplicateScan = () => {
    const engine = useDataEngine()
    const { schemas, error: schemasError } = useTranslatableSchemas()
    const [state, setState] = useState<ScanState>(INITIAL_STATE)
    // Increments to invalidate an in-flight scan (rescan or unmount)
    const scanIdRef = useRef(0)

    const runScan = useCallback(
        async (types: TranslatableSchema[]) => {
            const scanId = ++scanIdRef.current
            const isCurrent = () => scanIdRef.current === scanId

            setState({
                status: 'scanning',
                progress: 0,
                duplicates: [],
                failedTypes: [],
            })

            const duplicates: DuplicateGroup[] = []
            const failedTypes: string[] = []

            for (const [index, type] of types.entries()) {
                try {
                    const response = (await engine.query({
                        objects: {
                            resource: type.plural,
                            params: {
                                fields: 'id,displayName,translations',
                                paging: false,
                            },
                        },
                    })) as {
                        objects: Record<string, TranslatedObject[]>
                    }
                    const objects = response.objects[type.plural] ?? []
                    duplicates.push(
                        ...buildDuplicateGroups(type.plural, objects)
                    )
                } catch (error) {
                    console.error(`Failed to fetch ${type.plural}:`, error)
                    failedTypes.push(type.plural)
                }
                if (!isCurrent()) {
                    return
                }
                setState((previous) => ({
                    ...previous,
                    progress: ((index + 1) / types.length) * 100,
                }))
            }

            if (isCurrent()) {
                setState({
                    status: 'done',
                    progress: 100,
                    duplicates,
                    failedTypes,
                })
            }
        },
        [engine]
    )

    useEffect(() => {
        if (schemas) {
            runScan(schemas)
        }
        return () => {
            // Invalidate the in-flight scan on unmount/schema change
            scanIdRef.current++
        }
    }, [schemas, runScan])

    const rescan = useCallback(() => {
        if (schemas) {
            runScan(schemas)
        }
    }, [schemas, runScan])

    const removeDuplicates = useCallback((keys: Set<string>) => {
        setState((previous) => ({
            ...previous,
            duplicates: previous.duplicates.filter(
                (group) =>
                    !keys.has(
                        `${group.objectType}|${group.objectId}|${group.locale}|${group.property}`
                    )
            ),
        }))
    }, [])

    if (schemasError) {
        return {
            state: {
                ...INITIAL_STATE,
                status: 'error' as const,
                error: schemasError,
            },
            rescan,
            removeDuplicates,
        }
    }

    return { state, rescan, removeDuplicates }
}
