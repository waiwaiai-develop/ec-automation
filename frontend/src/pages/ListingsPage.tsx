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
import { ShoppingCart, Eye, Heart, TrendingUp, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
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
      header: 'プラットフォーム',
      cell: ({ getValue }) => <PlatformBadge platform={getValue() as string} />,
      size: 120,
    },
    {
      accessorKey: 'title_en',
      header: 'タイトル',
      cell: ({ row }) => (
        <Link
          to={`/products/${row.original.product_id}`}
          className="text-sm font-medium hover:text-primary hover:underline transition-colors line-clamp-1"
        >
          {row.original.title_en || '-'}
        </Link>
      ),
    },
    {
      accessorKey: 'price_usd',
      header: '価格',
      cell: ({ getValue }) => <span className="font-semibold tabular-nums">{formatPrice(getValue() as number | null, 'USD')}</span>,
      size: 100,
    },
    {
      accessorKey: 'status',
      header: 'ステータス',
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
      header: () => <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-pink-500" />お気に入り</span>,
      cell: ({ getValue }) => {
        const v = getValue() as number
        return <span className={`tabular-nums ${v > 0 ? 'text-pink-600 font-medium' : 'text-muted-foreground'}`}>{v ?? '-'}</span>
      },
      size: 70,
    },
    {
      accessorKey: 'sales',
      header: () => <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3 text-emerald-500" />販売数</span>,
      cell: ({ getValue }) => {
        const v = getValue() as number
        return <span className={`tabular-nums ${v > 0 ? 'text-emerald-600 font-bold' : 'text-muted-foreground'}`}>{v ?? '-'}</span>
      },
      size: 70,
    },
    {
      accessorKey: 'updated_at',
      header: '更新日',
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

  // プラットフォームタブ
  const platformTabs = [
    { value: '', label: 'すべて' },
    { value: 'ebay', label: 'eBay' },
    { value: 'base', label: 'BASE' },
  ]

  const filters: FilterOption[] = [
    {
      id: 'status',
      label: 'ステータス',
      value: status,
      options: [
        { value: ' ', label: 'すべて' },
        { value: 'active', label: '出品中' },
        { value: 'draft', label: '下書き' },
        { value: 'ended', label: '終了' },
      ],
      onChange: (v) => updateParams({ status: v.trim(), offset: '' }),
    },
  ]

  const activeFilters: { label: string; onRemove: () => void }[] = []
  if (status) activeFilters.push({ label: `ステータス: ${status}`, onRemove: () => updateParams({ status: '' }) })

  return (
    <div className="space-y-5">
      {/* プラットフォームタブ */}
      <div className="flex items-center gap-1 rounded-lg border p-1 w-fit">
        {platformTabs.map((tab) => (
          <Button
            key={tab.value}
            variant={platform === tab.value ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 px-3 text-xs"
            onClick={() => updateParams({ platform: tab.value, offset: '' })}
          >
            {tab.label}
          </Button>
        ))}
      </div>

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
                        icon={ShoppingCart}
                        title="リスティングがありません"
                        description="商品詳細ページから出品を開始しましょう"
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
