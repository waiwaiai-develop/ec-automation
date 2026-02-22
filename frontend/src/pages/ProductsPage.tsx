import { useState, useMemo, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { Trash2, Upload, ExternalLink, Package, CheckSquare, ArrowUpDown, ArrowUp, ArrowDown, Search } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { StockBadge, DSFlagBadge, PlatformBadge } from '@/components/shared/Badges'
import { Pagination } from '@/components/shared/Pagination'
import { ErrorState } from '@/components/shared/ErrorState'
import { useApi } from '@/hooks/use-api'
import { getProducts, importNetseaUrl, bulkDelete, bulkSetFlags, bulkList } from '@/lib/api'
import { formatPrice, parseImages } from '@/lib/formatters'
import type { Product } from '@/types'

const PAGE_SIZE = 50

export function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // URLからフィルター状態を復元
  const category = searchParams.get('category') || ''
  const stockStatus = searchParams.get('stock_status') || ''
  const dsOnly = searchParams.get('ds_only') || ''
  const searchQuery = searchParams.get('search') || ''
  const offset = Number(searchParams.get('offset') || '0')

  const [netseaUrl, setNetseaUrl] = useState('')
  const [importing, setImporting] = useState(false)
  const [rowSelection, setRowSelection] = useState<Record<string, boolean>>({})
  const [sorting, setSorting] = useState<SortingState>([])
  const [localSearch, setLocalSearch] = useState(searchQuery)

  // 一括出品ダイアログ
  const [bulkListDialog, setBulkListDialog] = useState<{ platform: string } | null>(null)
  const [bulkListPrice, setBulkListPrice] = useState('25.00')

  // URLパラメータ更新ヘルパー
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
    () => getProducts({
      category: category || undefined,
      stock_status: stockStatus || undefined,
      ds_only: dsOnly || undefined,
      search: searchQuery || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [category, stockStatus, dsOnly, searchQuery, offset],
    { debounceMs: searchQuery !== localSearch ? 300 : 0 }
  )

  // 準備状況の計算
  function getReadinessScore(p: Product): { score: number; max: number; items: { label: string; done: boolean }[] } {
    const items = [
      { label: '英語タイトル', done: !!p.name_en },
      { label: '英語説明', done: !!p.description_en },
      { label: '出品フラグ', done: p.list_on_ebay === 1 || p.list_on_base === 1 },
    ]
    return { score: items.filter(i => i.done).length, max: items.length, items }
  }

  const columns = useMemo<ColumnDef<Product>[]>(() => [
    {
      id: 'select',
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={(v) => table.toggleAllPageRowsSelected(!!v)}
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(v) => row.toggleSelected(!!v)}
        />
      ),
      size: 40,
      enableSorting: false,
    },
    {
      accessorKey: 'image_urls',
      header: '',
      cell: ({ getValue }) => {
        const imgs = parseImages(getValue() as string)
        return imgs.length > 0 ? (
          <img src={imgs[0]} alt="" className="h-10 w-10 rounded-lg object-cover ring-1 ring-border" />
        ) : (
          <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
            <Package className="h-4 w-4 text-muted-foreground/40" />
          </div>
        )
      },
      size: 56,
      enableSorting: false,
    },
    {
      accessorKey: 'name_ja',
      header: '商品名',
      cell: ({ row }) => (
        <Link
          to={`/products/${row.original.id}`}
          className="font-medium text-sm hover:text-blue-600 hover:underline transition-colors line-clamp-2"
        >
          {row.original.name_ja}
        </Link>
      ),
    },
    {
      accessorKey: 'category',
      header: 'カテゴリ',
      cell: ({ getValue }) => {
        const cat = getValue() as string | null
        if (!cat) return <span className="text-muted-foreground">-</span>
        return (
          <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs font-medium">
            {cat}
          </span>
        )
      },
    },
    {
      accessorKey: 'wholesale_price_jpy',
      header: '卸値',
      cell: ({ getValue }) => {
        const v = getValue() as number | null
        return <span className="tabular-nums font-medium">{formatPrice(v)}</span>
      },
    },
    {
      accessorKey: 'stock_status',
      header: '在庫',
      cell: ({ getValue }) => <StockBadge status={getValue() as string | null} />,
    },
    {
      id: 'readiness',
      header: '準備状況',
      cell: ({ row }) => {
        const r = getReadinessScore(row.original)
        const colorClass = r.score === r.max ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
          : r.score > 0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
          : 'bg-muted text-muted-foreground'
        return (
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="outline" className={`text-xs px-1.5 py-0 ${colorClass}`}>
                {r.score}/{r.max}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <div className="space-y-1 text-xs">
                {r.items.map((item, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className={item.done ? 'text-emerald-500' : 'text-muted-foreground'}>
                      {item.done ? '✓' : '✗'}
                    </span>
                    {item.label}
                  </div>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        )
      },
      enableSorting: false,
    },
    {
      id: 'platforms',
      header: '出品先',
      cell: ({ row }) => {
        const p = row.original
        const hasPlatform = p.list_on_ebay === 1 || p.list_on_base === 1
        return (
          <div className="flex gap-1">
            {p.list_on_ebay === 1 && <PlatformBadge platform="ebay" />}
            {p.list_on_base === 1 && <PlatformBadge platform="base" />}
            {!hasPlatform && <span className="text-xs text-muted-foreground">--</span>}
          </div>
        )
      },
      enableSorting: false,
    },
    {
      id: 'ds',
      header: 'DS',
      cell: ({ row }) => {
        const p = row.original
        return <DSFlagBadge direct={p.direct_send_flag} image={p.image_copy_flag} shop={p.deal_net_shop_flag} />
      },
      enableSorting: false,
    },
  ], [])

  const products = data?.products ?? []

  const table = useReactTable({
    data: products,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    state: { rowSelection, sorting },
    getRowId: (row) => String(row.id),
  })

  const selectedIds = Object.keys(rowSelection)
    .filter((k) => rowSelection[k])
    .map(Number)

  async function handleImport() {
    if (!netseaUrl.trim()) return
    setImporting(true)
    try {
      const res = await importNetseaUrl(netseaUrl.trim())
      toast.success(res.message)
      setNetseaUrl('')
      refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setImporting(false) }
  }

  async function handleBulkDelete() {
    if (selectedIds.length === 0) return
    try {
      const res = await bulkDelete(selectedIds)
      toast.success(res.message); setRowSelection({}); refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
  }

  async function handleBulkFlag(flag: string, value: number) {
    if (selectedIds.length === 0) return
    try {
      const res = await bulkSetFlags(selectedIds, { [flag]: value })
      toast.success(res.message); refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
  }

  async function handleBulkList(platform: string, priceUsd: number) {
    if (selectedIds.length === 0) return
    try {
      const res = await bulkList({
        product_ids: selectedIds, platform,
        auto_generate: true, price_usd: priceUsd,
      })
      toast.success(res.message); refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
  }

  // ソートアイコンヘルパー
  function SortIcon({ column }: { column: string }) {
    const s = sorting.find(s => s.id === column)
    if (!s) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-30" />
    return s.desc
      ? <ArrowDown className="h-3 w-3 ml-1" />
      : <ArrowUp className="h-3 w-3 ml-1" />
  }

  return (
    <div className="space-y-5">
      {/* NETSEA URLインポート */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Upload className="h-4 w-4 text-muted-foreground" />
            NETSEA商品登録
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="https://www.netsea.jp/shop/XXXXX/YYYYY"
              value={netseaUrl}
              onChange={(e) => setNetseaUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleImport()}
              className="h-10"
            />
            <Button onClick={handleImport} disabled={importing}>
              <Upload className="mr-2 h-4 w-4" />
              {importing ? '登録中...' : '登録'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* フィルター + 検索 */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground">Filter:</span>
        <Select
          value={category}
          onValueChange={(v) => updateParams({ category: v.trim(), offset: '' })}
        >
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="カテゴリ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">すべて</SelectItem>
            {(data?.categories ?? []).map((c) => (
              <SelectItem key={c} value={c}>{c}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={stockStatus}
          onValueChange={(v) => updateParams({ stock_status: v.trim(), offset: '' })}
        >
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="在庫状態" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">すべて</SelectItem>
            <SelectItem value="in_stock">在庫あり</SelectItem>
            <SelectItem value="out_of_stock">在庫切れ</SelectItem>
            <SelectItem value="limited">残りわずか</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={dsOnly}
          onValueChange={(v) => updateParams({ ds_only: v.trim(), offset: '' })}
        >
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="DS対応" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value=" ">すべて</SelectItem>
            <SelectItem value="1">DS対応のみ</SelectItem>
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

      {/* 一括操作バー */}
      {selectedIds.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border p-3">
          <div className="flex items-center gap-1.5">
            <CheckSquare className="h-4 w-4" />
            <span className="text-sm font-semibold">{selectedIds.length}件選択</span>
          </div>
          <div className="h-4 w-px bg-border mx-1" />

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm" className="h-7">
                <Trash2 className="mr-1 h-3 w-3" />
                削除
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>商品を削除しますか？</AlertDialogTitle>
                <AlertDialogDescription>
                  {selectedIds.length}件の商品と関連リスティングが削除されます。この操作は取り消せません。
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>キャンセル</AlertDialogCancel>
                <AlertDialogAction onClick={handleBulkDelete}>削除する</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <Button variant="outline" size="sm" className="h-7" onClick={() => handleBulkFlag('list_on_ebay', 1)}>
            eBay ON
          </Button>
          <Button variant="outline" size="sm" className="h-7" onClick={() => handleBulkFlag('list_on_ebay', 0)}>
            eBay OFF
          </Button>
          <Button variant="outline" size="sm" className="h-7" onClick={() => handleBulkFlag('list_on_base', 1)}>
            BASE ON
          </Button>
          <Button variant="outline" size="sm" className="h-7" onClick={() => handleBulkFlag('list_on_base', 0)}>
            BASE OFF
          </Button>
          <Button size="sm" className="h-7" onClick={() => setBulkListDialog({ platform: 'ebay' })}>
            <ExternalLink className="mr-1 h-3 w-3" />
            eBay一括出品
          </Button>
          <Button size="sm" className="h-7" onClick={() => setBulkListDialog({ platform: 'base' })}>
            <ExternalLink className="mr-1 h-3 w-3" />
            BASE一括出品
          </Button>
        </div>
      )}

      {/* 一括出品価格入力ダイアログ */}
      <Dialog open={!!bulkListDialog} onOpenChange={(open) => !open && setBulkListDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>一括出品 - {bulkListDialog?.platform?.toUpperCase()}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-muted-foreground">
              {selectedIds.length}件の商品を出品します。販売価格を入力してください。
            </p>
            <div>
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                販売価格 (USD)
              </Label>
              <Input
                type="number"
                step="0.01"
                value={bulkListPrice}
                onChange={(e) => setBulkListPrice(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkListDialog(null)}>キャンセル</Button>
            <Button onClick={() => {
              if (bulkListDialog) {
                handleBulkList(bulkListDialog.platform, parseFloat(bulkListPrice))
                setBulkListDialog(null)
              }
            }}>
              出品する
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* テーブル */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
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
                        <Package className="h-8 w-8 mb-2 opacity-30" />
                        <p className="text-sm font-medium">商品がありません</p>
                        <p className="text-xs mt-1">上のフォームからNETSEA URLで商品を登録しましょう</p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id} data-state={row.getIsSelected() && 'selected'} className="hover:bg-muted/30">
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
