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
} from '@dhis2/ui'
import React from 'react'
import { DuplicateGroup, duplicateGroupKey } from '../lib/translationTypes'
import styles from './DuplicatesTable.module.css'

interface DuplicatesTableProps {
    duplicates: DuplicateGroup[]
    selectedKeys: Set<string>
    /** rowKey -> index of the chosen value within group.values (default 0) */
    chosenValues: Map<string, number>
    disabled: boolean
    onToggleRow: (rowKey: string) => void
    onToggleAll: (select: boolean) => void
    onChooseValue: (rowKey: string, valueIndex: number) => void
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
    const allSelected =
        duplicates.length > 0 && selectedKeys.size === duplicates.length

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
                            disabled={disabled}
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
                {duplicates.map((group) => {
                    const rowKey = duplicateGroupKey(group)
                    const chosenIndex = chosenValues.get(rowKey) ?? 0
                    return (
                        <DataTableRow
                            key={rowKey}
                            selected={selectedKeys.has(rowKey)}
                            dataTest="duplicate-row"
                        >
                            <DataTableCell>
                                <Checkbox
                                    dataTest="row-checkbox"
                                    checked={selectedKeys.has(rowKey)}
                                    disabled={disabled}
                                    onChange={() => onToggleRow(rowKey)}
                                />
                            </DataTableCell>
                            <DataTableCell>{group.objectType}</DataTableCell>
                            <DataTableCell>{group.objectId}</DataTableCell>
                            <DataTableCell>{group.objectName}</DataTableCell>
                            <DataTableCell>{group.locale}</DataTableCell>
                            <DataTableCell>{group.property}</DataTableCell>
                            <DataTableCell>
                                <div className={styles.valueList}>
                                    {group.values.map((value, index) => (
                                        <Radio
                                            // Values may be identical strings,
                                            // so the index is part of the key
                                            key={`${index}-${value}`}
                                            dense
                                            name={rowKey}
                                            label={value}
                                            checked={chosenIndex === index}
                                            disabled={disabled}
                                            onChange={() =>
                                                onChooseValue(rowKey, index)
                                            }
                                        />
                                    ))}
                                </div>
                            </DataTableCell>
                        </DataTableRow>
                    )
                })}
            </DataTableBody>
        </DataTable>
    )
}
