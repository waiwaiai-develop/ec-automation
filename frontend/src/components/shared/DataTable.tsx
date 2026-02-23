import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type TableOptions,
} from '@tanstack/react-table'
import { useState } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Pagination } from '@/components/shared/Pagination'
import { EmptyState } from '@/components/shared/EmptyState'
import type { LucideIcon } from 'lucide-react'

interface DataTableProps<TData> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<TData, any>[]
  data: TData[]
  loading?: boolean
  // ページネーション
  pagination?: {
    offset: number
    limit: number
    total: number
    onPageChange: (offset: number) => void
  }
  // 行選択
  rowSelection?: RowSelectionState
  onRowSelectionChange?: (selection: RowSelectionState) => void
  getRowId?: (row: TData) => string
  // 空状態
  emptyIcon?: LucideIcon
  emptyTitle?: string
  emptyDescription?: string
  // ソート
  sorting?: SortingState
  onSortingChange?: (sorting: SortingState) => void
  // 行クリック
  onRowClick?: (row: TData) => void
  // 行展開
  renderExpandedRow?: (row: TData) => React.ReactNode
}

export function DataTable<TData>({
  columns,
  data,
  loading,
  pagination,
  rowSelection,
  onRowSelectionChange,
  getRowId,
  emptyIcon,
  emptyTitle = 'データがありません',
  emptyDescription,
  sorting: externalSorting,
  onSortingChange: externalOnSortingChange,
  onRowClick,
  renderExpandedRow,
}: DataTableProps<TData>) {
  const [internalSorting, setInternalSorting] = useState<SortingState>([])
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({})

  const sorting = externalSorting ?? internalSorting
  const onSortingChange = externalOnSortingChange ?? setInternalSorting

  const tableOptions: TableOptions<TData> = {
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: (updater) => {
      const newVal = typeof updater === 'function' ? updater(sorting) : updater
      onSortingChange(newVal)
    },
    state: {
      sorting,
      ...(rowSelection !== undefined ? { rowSelection } : {}),
    },
    ...(onRowSelectionChange ? { onRowSelectionChange: (updater) => {
      const newVal = typeof updater === 'function' ? updater(rowSelection ?? {}) : updater
      onRowSelectionChange(newVal)
    }} : {}),
    ...(getRowId ? { getRowId } : {}),
  }

  const table = useReactTable(tableOptions)

  function SortIcon({ column }: { column: string }) {
    const s = sorting.find(s => s.id === column)
    if (!s) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-30" />
    return s.desc ? <ArrowDown className="h-3 w-3 ml-1" /> : <ArrowUp className="h-3 w-3 ml-1" />
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 rounded-lg" />
        ))}
      </div>
    )
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id} className="bg-muted/30">
                {hg.headers.map((h) => (
                  <TableHead
                    key={h.id}
                    style={{ width: h.getSize() !== 150 ? h.getSize() : undefined }}
                    className={h.column.getCanSort() ? 'cursor-pointer select-none hover:text-foreground' : ''}
                    onClick={h.column.getCanSort() ? h.column.getToggleSortingHandler() : undefined}
                  >
                    <span className="flex items-center">
                      {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getCanSort() && <SortIcon column={h.column.id} />}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="p-0">
                  {emptyIcon ? (
                    <EmptyState
                      icon={emptyIcon}
                      title={emptyTitle}
                      description={emptyDescription}
                    />
                  ) : (
                    <div className="flex flex-col items-center py-12 text-muted-foreground">
                      <p className="text-sm font-medium">{emptyTitle}</p>
                      {emptyDescription && <p className="text-xs mt-1">{emptyDescription}</p>}
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => {
                const rowId = row.id
                const isExpanded = expandedRows[rowId]
                return (
                  <TableRow
                    key={rowId}
                    data-state={row.getIsSelected() && 'selected'}
                    className={`hover:bg-muted/30 ${onRowClick ? 'cursor-pointer' : ''} ${renderExpandedRow ? 'cursor-pointer' : ''}`}
                    onClick={() => {
                      if (onRowClick) onRowClick(row.original)
                      if (renderExpandedRow) {
                        setExpandedRows(prev => ({ ...prev, [rowId]: !prev[rowId] }))
                      }
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                    {/* 展開行 */}
                    {renderExpandedRow && isExpanded && (
                      <TableCell colSpan={columns.length} className="bg-muted/20 p-4">
                        {renderExpandedRow(row.original)}
                      </TableCell>
                    )}
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
        {pagination && pagination.total > 0 && (
          <Pagination
            offset={pagination.offset}
            limit={pagination.limit}
            total={pagination.total}
            onPageChange={pagination.onPageChange}
          />
        )}
      </CardContent>
    </Card>
  )
}
