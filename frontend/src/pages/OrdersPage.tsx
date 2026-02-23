import { useState, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { ClipboardList, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

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
import { PlatformBadge, StatusBadge } from '@/components/shared/Badges'
import { FilterBar, type FilterOption } from '@/components/shared/FilterBar'
import { EmptyState } from '@/components/shared/EmptyState'
import { Pagination } from '@/components/shared/Pagination'
import { ErrorState } from '@/components/shared/ErrorState'
import { useApi } from '@/hooks/use-api'
import { getOrders } from '@/lib/api'
import { formatPrice, formatDate } from '@/lib/formatters'
import type { Order } from '@/types'

const PAGE_SIZE = 50

// ステータスカンバン用の定義
const statusFlow = [
  { key: 'pending', label: '保留', color: 'bg-blue-500' },
  { key: 'purchased', label: '仕入済', color: 'bg-indigo-500' },
  { key: 'shipped', label: '発送済', color: 'bg-cyan-500' },
  { key: 'delivered', label: '配達済', color: 'bg-emerald-500' },
]

export function OrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const platform = searchParams.get('platform') || ''
  const status = searchParams.get('status') || ''
  const searchQuery = searchParams.get('search') || ''
  const offset = Number(searchParams.get('offset') || '0')

  const [localSearch, setLocalSearch] = useState(searchQuery)
  const [sorting, setSorting] = useState<SortingState>([])

  const updateParams = useCallback((updates: Record<string, string>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      for (const [k, v] of Object.entries(updates)) {
        if (v) next.set(k, v)
        else next.delete(k)
      }
      return next
    })
  }, [setSearchParams])

  const { data, loading, error, refetch } = useApi(
    () => getOrders({
      platform: platform || undefined,
      status: status || undefined,
      search: searchQuery || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [platform, status, searchQuery, offset]
  )

  const orders = data?.orders ?? []

  // カンバンビュー用: ステータス別件数
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const o of orders) {
      counts[o.status] = (counts[o.status] || 0) + 1
    }
    return counts
  }, [orders])

  const columns = useMemo<ColumnDef<Order>[]>(() => [
    {
      accessorKey: 'platform',
      header: 'プラットフォーム',
      cell: ({ getValue }) => <PlatformBadge platform={getValue() as string} />,
      size: 120,
    },
    {
      accessorKey: 'platform_order_id',
      header: '注文ID',
      cell: ({ getValue }) => {
        const v = getValue() as string
        return v ? <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{v}</span> : <span className="text-muted-foreground">-</span>
      },
      size: 140,
    },
    {
      accessorKey: 'buyer_name',
      header: '購入者',
      cell: ({ getValue }) => (getValue() as string) || <span className="text-muted-foreground">-</span>,
    },
    {
      accessorKey: 'buyer_country',
      header: '国',
      cell: ({ getValue }) => {
        const c = getValue() as string
        return c ? (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium">
            {c}
          </span>
        ) : <span className="text-muted-foreground">-</span>
      },
      size: 80,
    },
    {
      accessorKey: 'sale_price_usd',
      header: '売上',
      cell: ({ getValue }) => <span className="font-semibold tabular-nums">{formatPrice(getValue() as number | null, 'USD')}</span>,
      size: 100,
    },
    {
      accessorKey: 'profit_usd',
      header: '利益',
      cell: ({ row }) => {
        const v = row.original.profit_usd
        const sale = row.original.sale_price_usd
        if (v == null) return <span className="text-muted-foreground">-</span>
        const margin = sale && sale > 0 ? v / sale : 0
        return (
          <div>
            <span className={`font-bold tabular-nums ${v > 0 ? 'text-emerald-600' : v < 0 ? 'text-red-600' : 'text-muted-foreground'}`}>
              {v > 0 ? '+' : ''}{formatPrice(v, 'USD')}
            </span>
            {margin !== 0 && (
              <span className={`ml-1 text-xs ${margin >= 0.25 ? 'text-emerald-500' : 'text-red-500'}`}>
                ({(margin * 100).toFixed(0)}%)
              </span>
            )}
          </div>
        )
      },
      size: 120,
    },
    {
      accessorKey: 'status',
      header: 'ステータス',
      cell: ({ getValue }) => <StatusBadge status={getValue() as string} />,
      size: 110,
    },
    {
      accessorKey: 'ordered_at',
      header: '注文日',
      cell: ({ getValue }) => <span className="text-xs text-muted-foreground tabular-nums">{formatDate(getValue() as string)}</span>,
      size: 100,
    },
  ], [])

  const table = useReactTable({
    data: orders,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
    getRowId: (row) => String(row.id),
  })

  function SortIcon({ column }: { column: string }) {
    const s = sorting.find(s => s.id === column)
    if (!s) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-30" />
    return s.desc ? <ArrowDown className="h-3 w-3 ml-1" /> : <ArrowUp className="h-3 w-3 ml-1" />
  }

  const filters: FilterOption[] = [
    {
      id: 'platform',
      label: 'プラットフォーム',
      value: platform,
      options: [
        { value: ' ', label: 'すべて' },
        { value: 'ebay', label: 'eBay' },
        { value: 'base', label: 'BASE' },
      ],
      onChange: (v) => updateParams({ platform: v.trim(), offset: '' }),
    },
    {
      id: 'status',
      label: 'ステータス',
      value: status,
      options: [
        { value: ' ', label: 'すべて' },
        { value: 'pending', label: '保留' },
        { value: 'purchased', label: '仕入済' },
        { value: 'shipped', label: '発送済' },
        { value: 'delivered', label: '配達済' },
        { value: 'cancelled', label: 'キャンセル' },
      ],
      onChange: (v) => updateParams({ status: v.trim(), offset: '' }),
    },
  ]

  const activeFilters: { label: string; onRemove: () => void }[] = []
  if (platform) activeFilters.push({ label: `プラットフォーム: ${platform}`, onRemove: () => updateParams({ platform: '' }) })
  if (status) activeFilters.push({ label: `ステータス: ${status}`, onRemove: () => updateParams({ status: '' }) })

  return (
    <div className="space-y-5">
      {/* ステータスカンバン（視覚的進捗表示） */}
      {orders.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {statusFlow.map((s) => {
            const count = statusCounts[s.key] || 0
            const isActive = status === s.key
            return (
              <Card
                key={s.key}
                className={`cursor-pointer transition-all hover:shadow-md ${isActive ? 'ring-2 ring-primary' : ''}`}
                onClick={() => updateParams({ status: isActive ? '' : s.key, offset: '' })}
              >
                <CardContent className="flex items-center gap-3 p-4">
                  <div className={`h-8 w-1 rounded-full ${s.color}`} />
                  <div>
                    <p className="text-xs text-muted-foreground">{s.label}</p>
                    <p className="text-xl font-bold tabular-nums">{count}</p>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* フィルター */}
      <FilterBar
        filters={filters}
        searchValue={localSearch}
        onSearchChange={(v) => {
          setLocalSearch(v)
          updateParams({ search: v, offset: '' })
        }}
        activeFilters={activeFilters}
      />

      {/* テーブル */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
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
                      <EmptyState
                        icon={ClipboardList}
                        title="注文がありません"
                        description="出品後、注文が入るとここに表示されます"
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id} className="hover:bg-muted/30">
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
            {data && data.total > 0 && (
              <Pagination
                offset={data.offset}
                limit={data.limit}
                total={data.total}
                onPageChange={(newOffset) => updateParams({ offset: String(newOffset) })}
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
