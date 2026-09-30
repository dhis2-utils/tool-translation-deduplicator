import i18n from '@dhis2/d2-i18n'
import {
    Checkbox,
    DataTable,
    DataTableBody,
    DataTableCell,
    DataTableColumnHeader,
    DataTableHead,
    DataTableRow,
    Radio,
    Tag,
} from '@dhis2/ui'
import React from 'react'
import {
    DuplicateGroup,
    duplicateGroupKey,
    UNFIXABLE_TYPES,
} from '../lib/translationTypes'
import styles from './DuplicatesTable.module.css'

interface DuplicatesTableProps {
    duplicates: DuplicateGroup[]
    selectedKeys: Set<string>
    /** rowKey -> index of the chosen value within group.values (default 0) */
    chosenValues: Map<string, number>
    disabled: boolean
    /** Toggles selection of the row's whole object (all its duplicate rows) */
    onToggleRow: (group: DuplicateGroup) => void
    onToggleAll: (select: boolean) => void
    onChooseValue: (rowKey: string, valueIndex: number) => void
}

/** Group adjacent rows belonging to the same object, preserving order. */
const groupByObject = (duplicates: DuplicateGroup[]): DuplicateGroup[][] => {
    const groups: DuplicateGroup[][] = []
    let current: DuplicateGroup[] | undefined
    let currentKey: string | undefined
    for (const duplicate of duplicates) {
        const key = `${duplicate.objectType}|${duplicate.objectId}`
        if (current && key === currentKey) {
            current.push(duplicate)
        } else {
            current = [duplicate]
            currentKey = key
            groups.push(current)
        }
    }
    return groups
}

export const DuplicatesTable = ({
    duplicates,
    selectedKeys,
    chosenValues,
    disabled,
    onToggleRow,
    onToggleAll,
    onChooseValue,
}: DuplicatesTableProps) => {
    const fixableCount = duplicates.filter(
        (group) => !UNFIXABLE_TYPES.has(group.objectType)
    ).length
    const allSelected = fixableCount > 0 && selectedKeys.size === fixableCount

    return (
        <DataTable className={styles.table}>
            <DataTableHead>
                <DataTableRow>
                    <DataTableColumnHeader width="48px">
                        <Checkbox
                            dataTest="select-all-checkbox"
                            checked={allSelected}
                            indeterminate={
                                selectedKeys.size > 0 && !allSelected
                            }
                            disabled={disabled || fixableCount === 0}
                            onChange={({ checked }) => onToggleAll(checked)}
                        />
                    </DataTableColumnHeader>
                    <DataTableColumnHeader>
                        {i18n.t('Object type')}
                    </DataTableColumnHeader>
                    <DataTableColumnHeader>
                        {i18n.t('ID')}
                    </DataTableColumnHeader>
                    <DataTableColumnHeader>
                        {i18n.t('Name')}
                    </DataTableColumnHeader>
                    <DataTableColumnHeader>
                        {i18n.t('Locale')}
                    </DataTableColumnHeader>
                    <DataTableColumnHeader>
                        {i18n.t('Property')}
                    </DataTableColumnHeader>
                    <DataTableColumnHeader>
                        {i18n.t('Translation to keep')}
                    </DataTableColumnHeader>
                </DataTableRow>
            </DataTableHead>
            <DataTableBody>
                {groupByObject(duplicates).map((objectRows) =>
                    objectRows.map((group, indexInObject) => {
                        const rowKey = duplicateGroupKey(group)
                        const chosenIndex = chosenValues.get(rowKey) ?? 0
                        const rowSpan = String(objectRows.length)
                        const unfixable = UNFIXABLE_TYPES.has(group.objectType)
                        return (
                            <DataTableRow
                                key={rowKey}
                                selected={selectedKeys.has(rowKey)}
                                dataTest={`duplicate-row-${group.objectId}-${group.locale}-${group.property}`}
                            >
                                {indexInObject === 0 && (
                                    <>
                                        <DataTableCell rowSpan={rowSpan}>
                                            {!unfixable && (
                                                <Checkbox
                                                    dataTest="row-checkbox"
                                                    checked={selectedKeys.has(
                                                        rowKey
                                                    )}
                                                    disabled={disabled}
                                                    onChange={() =>
                                                        onToggleRow(group)
                                                    }
                                                />
                                            )}
                                        </DataTableCell>
                                        <DataTableCell rowSpan={rowSpan}>
                                            {group.objectType}
                                        </DataTableCell>
                                        <DataTableCell rowSpan={rowSpan}>
                                            {group.objectId}
                                        </DataTableCell>
                                        <DataTableCell rowSpan={rowSpan}>
                                            {group.objectName}
                                        </DataTableCell>
                                    </>
                                )}
                                <DataTableCell>{group.locale}</DataTableCell>
                                <DataTableCell>{group.property}</DataTableCell>
                                <DataTableCell>
                                    <div className={styles.valueList}>
                                        {unfixable ? (
                                            <>
                                                <Tag neutral>
                                                    {i18n.t(
                                                        'Cannot be fixed via API'
                                                    )}
                                                </Tag>
                                                {group.values.map(
                                                    (value, index) => (
                                                        <span
                                                            key={`${index}-${value}`}
                                                            className={
                                                                styles.mutedValue
                                                            }
                                                        >
                                                            {value}
                                                        </span>
                                                    )
                                                )}
                                            </>
                                        ) : (
                                            group.values.map((value, index) => (
                                                <Radio
                                                    // Values may be identical
                                                    // strings, so the index is
                                                    // part of the key
                                                    key={`${index}-${value}`}
                                                    dense
                                                    name={rowKey}
                                                    label={value}
                                                    checked={
                                                        chosenIndex === index
                                                    }
                                                    disabled={disabled}
                                                    onChange={() =>
                                                        onChooseValue(
                                                            rowKey,
                                                            index
                                                        )
                                                    }
                                                />
                                            ))
                                        )}
                                    </div>
                                </DataTableCell>
                            </DataTableRow>
                        )
                    })
                )}
            </DataTableBody>
        </DataTable>
    )
}
