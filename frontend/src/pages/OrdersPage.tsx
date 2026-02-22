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
import { ShoppingCart, Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { Pagination } from '@/components/shared/Pagination'
import { ErrorState } from '@/components/shared/ErrorState'
import { useApi } from '@/hooks/use-api'
import { getOrders } from '@/lib/api'
import { formatPrice, formatDate } from '@/lib/formatters'
import type { Order } from '@/types'

const PAGE_SIZE = 50

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

  const columns = useMemo<ColumnDef<Order>[]>(() => [
    {
      accessorKey: 'platform',
      header: 'Platform',
      cell: ({ getValue }) => <PlatformBadge platform={getValue() as string} />,
      size: 120,
    },
    {
      accessorKey: 'platform_order_id',
      header: 'Order ID',
      cell: ({ getValue }) => {
        const v = getValue() as string
        return v ? <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{v}</span> : <span className="text-muted-foreground">-</span>
      },
      size: 140,
    },
    {
      accessorKey: 'buyer_name',
      header: 'Buyer',
      cell: ({ getValue }) => (getValue() as string) || <span className="text-muted-foreground">-</span>,
    },
    {
      accessorKey: 'buyer_country',
      header: 'Country',
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
      header: 'Revenue',
      cell: ({ getValue }) => <span className="font-semibold tabular-nums">{formatPrice(getValue() as number | null, 'USD')}</span>,
      size: 100,
    },
    {
      accessorKey: 'profit_usd',
      header: 'Profit',
      cell: ({ getValue }) => {
        const v = getValue() as number | null
        if (v == null) return <span className="text-muted-foreground">-</span>
        return (
          <span className={`font-bold tabular-nums ${v > 0 ? 'text-emerald-600' : v < 0 ? 'text-red-600' : 'text-muted-foreground'}`}>
            {v > 0 ? '+' : ''}{formatPrice(v, 'USD')}
          </span>
        )
      },
      size: 100,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ getValue }) => <StatusBadge status={getValue() as string} />,
      size: 110,
    },
    {
      accessorKey: 'ordered_at',
      header: 'Date',
      cell: ({ getValue }) => <span className="text-xs text-muted-foreground tabular-nums">{formatDate(getValue() as string)}</span>,
      size: 100,
    },
  ], [])

  const orders = data?.orders ?? []

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

  return (
    <div className="space-y-5">
      {/* フィルター */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-muted-foreground">Filter:</span>
        <Select value={platform} onValueChange={(v) => updateParams({ platform: v.trim(), offset: '' })}>
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="Platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">すべて</SelectItem>
            <SelectItem value="ebay">eBay</SelectItem>
            <SelectItem value="base">BASE</SelectItem>
          </SelectContent>
        </Select>

        <Select value={status} onValueChange={(v) => updateParams({ status: v.trim(), offset: '' })}>
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">すべて</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="purchased">Purchased</SelectItem>
            <SelectItem value="shipped">Shipped</SelectItem>
            <SelectItem value="delivered">Delivered</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative ml-auto">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="検索..."
            value={localSearch}
            onChange={(e) => {
              setLocalSearch(e.target.value)
              updateParams({ search: e.target.value, offset: '' })
            }}
            className="h-9 w-[200px] pl-8"
          />
        </div>
      </div>

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
                    <TableCell colSpan={columns.length} className="text-center py-12">
                      <div className="flex flex-col items-center text-muted-foreground">
                        <ShoppingCart className="h-8 w-8 mb-2 opacity-30" />
                        <p className="text-sm font-medium">注文がありません</p>
                        <p className="text-xs mt-1">出品後、注文が入るとここに表示されます</p>
                      </div>
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
