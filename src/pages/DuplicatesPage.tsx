import i18n from '@dhis2/d2-i18n'
import {
    Button,
    ButtonStrip,
    CircularLoader,
    LinearLoader,
    NoticeBox,
} from '@dhis2/ui'
import React, { useCallback, useState } from 'react'
import { DuplicatesTable } from '../components/DuplicatesTable'
import { useDuplicateScan } from '../hooks/useDuplicateScan'
import {
    FailedObject,
    FixSelection,
    useFixDuplicates,
} from '../hooks/useFixDuplicates'
import {
    DuplicateGroup,
    duplicateGroupKey,
    UNFIXABLE_TYPES,
} from '../lib/translationTypes'
import styles from './DuplicatesPage.module.css'

export const DuplicatesPage = () => {
    const { state, rescan, removeDuplicates } = useDuplicateScan()
    const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set())
    const [chosenValues, setChosenValues] = useState<Map<string, number>>(
        new Map()
    )
    const [fixErrors, setFixErrors] = useState<FailedObject[]>([])

    const { fixDuplicates, isFixing } = useFixDuplicates({
        onComplete: (result) => {
            removeDuplicates(result.fixedKeys)
            setSelectedKeys(
                (previous) =>
                    new Set(
                        [...previous].filter(
                            (key) => !result.fixedKeys.has(key)
                        )
                    )
            )
            setFixErrors(result.failedObjects)
        },
    })

    // Selection operates on whole objects: the fix rewrites the full
    // object, and the server rejects any object that still contains a
    // duplicate pair (E1106) — so an object's duplicate rows can only be
    // fixed together.
    const handleToggleRow = useCallback(
        (group: DuplicateGroup) => {
            const siblingKeys = state.duplicates
                .filter(
                    (d) =>
                        d.objectType === group.objectType &&
                        d.objectId === group.objectId
                )
                .map(duplicateGroupKey)
            const isSelected = selectedKeys.has(duplicateGroupKey(group))
            setSelectedKeys((previous) => {
                const next = new Set(previous)
                for (const key of siblingKeys) {
                    if (isSelected) {
                        next.delete(key)
                    } else {
                        next.add(key)
                    }
                }
                return next
            })
        },
        [state.duplicates, selectedKeys]
    )

    const handleToggleAll = useCallback(
        (select: boolean) => {
            setSelectedKeys(
                select
                    ? new Set(
                          state.duplicates
                              .filter(
                                  (group) =>
                                      !UNFIXABLE_TYPES.has(group.objectType)
                              )
                              .map(duplicateGroupKey)
                      )
                    : new Set()
            )
        },
        [state.duplicates]
    )

    const handleChooseValue = useCallback(
        (rowKey: string, valueIndex: number) => {
            setChosenValues((previous) =>
                new Map(previous).set(rowKey, valueIndex)
            )
        },
        []
    )

    const handleFix = () => {
        const selections: FixSelection[] = state.duplicates
            .filter((group) => selectedKeys.has(duplicateGroupKey(group)))
            .map((group) => ({
                group,
                selectedValue:
                    group.values[
                        chosenValues.get(duplicateGroupKey(group)) ?? 0
                    ],
            }))
        setFixErrors([])
        fixDuplicates(selections)
    }

    const handleRescan = () => {
        setSelectedKeys(new Set())
        setChosenValues(new Map())
        setFixErrors([])
        rescan()
    }

    if (state.status === 'loading-schemas') {
        return (
            <div className={styles.centered}>
                <CircularLoader aria-label={i18n.t('Loading')} />
            </div>
        )
    }

    if (state.status === 'error') {
        return (
            <div className={styles.container}>
                <NoticeBox error title={i18n.t('Failed to load metadata')}>
                    {state.error?.message ??
                        i18n.t('An unknown error occurred')}
                </NoticeBox>
            </div>
        )
    }

    if (state.status === 'scanning') {
        return (
            <div className={styles.centered} data-test="scan-progress">
                <p>{i18n.t('Scanning metadata for duplicate translations…')}</p>
                <LinearLoader
                    amount={state.progress}
                    width="400px"
                    aria-label={i18n.t('Scan progress')}
                />
            </div>
        )
    }

    return (
        <div className={styles.container}>
            <h1 className={styles.title}>{i18n.t('Duplicate translations')}</h1>
            {fixErrors.length > 0 && (
                <NoticeBox
                    error
                    className={styles.notice}
                    title={i18n.t('Some updates failed')}
                    dataTest="fix-errors-notice"
                >
                    <ul className={styles.errorList}>
                        {fixErrors.map((failure) => (
                            <li key={failure.objectId}>
                                {failure.objectName} ({failure.objectId}) —{' '}
                                {failure.message}
                            </li>
                        ))}
                    </ul>
                </NoticeBox>
            )}
            {state.failedTypes.length > 0 && (
                <NoticeBox
                    warning
                    className={styles.notice}
                    title={i18n.t('Some object types could not be checked')}
                >
                    {i18n.t(
                        'The following types were skipped because of missing access or an error — {{types}}',
                        { types: state.failedTypes.join(', ') }
                    )}
                </NoticeBox>
            )}
            {state.duplicates.length === 0 ? (
                <>
                    <NoticeBox
                        valid
                        className={styles.notice}
                        title={i18n.t('No duplicate translations found')}
                    >
                        {i18n.t(
                            'All checked metadata has at most one translation per locale and property.'
                        )}
                    </NoticeBox>
                    <ButtonStrip>
                        <Button onClick={handleRescan} dataTest="rescan-button">
                            {i18n.t('Rescan')}
                        </Button>
                    </ButtonStrip>
                </>
            ) : (
                <>
                    <div className={styles.toolbar}>
                        <ButtonStrip>
                            <Button
                                primary
                                loading={isFixing}
                                disabled={selectedKeys.size === 0 || isFixing}
                                onClick={handleFix}
                                dataTest="fix-selected-button"
                            >
                                {i18n.t('Fix selected ({{selected}})', {
                                    selected: selectedKeys.size,
                                })}
                            </Button>
                            <Button
                                onClick={handleRescan}
                                disabled={isFixing}
                                dataTest="rescan-button"
                            >
                                {i18n.t('Rescan')}
                            </Button>
                        </ButtonStrip>
                    </div>
                    <DuplicatesTable
                        duplicates={state.duplicates}
                        selectedKeys={selectedKeys}
                        chosenValues={chosenValues}
                        disabled={isFixing}
                        onToggleRow={handleToggleRow}
                        onToggleAll={handleToggleAll}
                        onChooseValue={handleChooseValue}
                    />
                </>
            )}
        </div>
    )
}
