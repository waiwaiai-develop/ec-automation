import { useMemo, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import { List, Eye, Heart, TrendingUp, Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

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
import { getListings } from '@/lib/api'
import { formatPrice, formatDate } from '@/lib/formatters'
import type { Listing } from '@/types'

const PAGE_SIZE = 50

export function ListingsPage() {
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
    () => getListings({
      platform: platform || undefined,
      status: status || undefined,
      search: searchQuery || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [platform, status, searchQuery, offset]
  )

  const columns = useMemo<ColumnDef<Listing>[]>(() => [
    {
      accessorKey: 'platform',
      header: 'Platform',
      cell: ({ getValue }) => <PlatformBadge platform={getValue() as string} />,
      size: 120,
    },
    {
      accessorKey: 'title_en',
      header: 'Title',
      cell: ({ row }) => (
        <Link
          to={`/products/${row.original.product_id}`}
          className="text-sm font-medium hover:text-blue-600 hover:underline transition-colors line-clamp-1"
        >
          {row.original.title_en || '-'}
        </Link>
      ),
    },
    {
      accessorKey: 'price_usd',
      header: 'Price',
      cell: ({ getValue }) => <span className="font-semibold tabular-nums">{formatPrice(getValue() as number | null, 'USD')}</span>,
      size: 100,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ getValue }) => <StatusBadge status={getValue() as string} />,
      size: 100,
    },
    {
      accessorKey: 'views',
      header: () => <span className="flex items-center gap-1"><Eye className="h-3 w-3" />PV</span>,
      cell: ({ getValue }) => {
        const v = getValue() as number
        return <span className="tabular-nums text-muted-foreground">{v ?? '-'}</span>
      },
      size: 70,
    },
    {
      accessorKey: 'favorites',
      header: () => <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-pink-500" />Fav</span>,
      cell: ({ getValue }) => {
        const v = getValue() as number
        return <span className={`tabular-nums ${v > 0 ? 'text-pink-600 font-medium' : 'text-muted-foreground'}`}>{v ?? '-'}</span>
      },
      size: 70,
    },
    {
      accessorKey: 'sales',
      header: () => <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3 text-emerald-500" />Sales</span>,
      cell: ({ getValue }) => {
        const v = getValue() as number
        return <span className={`tabular-nums ${v > 0 ? 'text-emerald-600 font-bold' : 'text-muted-foreground'}`}>{v ?? '-'}</span>
      },
      size: 70,
    },
    {
      accessorKey: 'updated_at',
      header: 'Updated',
      cell: ({ getValue }) => <span className="text-xs text-muted-foreground tabular-nums">{formatDate(getValue() as string)}</span>,
      size: 100,
    },
  ], [])

  const listings = data?.listings ?? []

  const table = useReactTable({
    data: listings,
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
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="ended">Ended</SelectItem>
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
                        <List className="h-8 w-8 mb-2 opacity-30" />
                        <p className="text-sm font-medium">リスティングがありません</p>
                        <p className="text-xs mt-1">商品詳細ページから出品を開始しましょう</p>
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
