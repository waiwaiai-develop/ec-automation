import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Search, ArrowLeft, TrendingUp, DollarSign, Users, Package,
  BarChart3, Loader2, ExternalLink, ShoppingCart,
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip, ResponsiveContainer } from 'recharts'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { StatCard } from '@/components/shared/StatCard'
import { ErrorState } from '@/components/shared/ErrorState'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useApi } from '@/hooks/use-api'
import { getResearchDetail, matchNetsea } from '@/lib/api'
import { formatPrice, formatMargin } from '@/lib/formatters'
import type { ResearchMatch } from '@/types'

export function ResearchDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [supplierIds, setSupplierIds] = useState('79841')
  const [matching, setMatching] = useState(false)
  const [matchResults, setMatchResults] = useState<ResearchMatch[]>([])

  const { data, loading, error, refetch } = useApi(
    () => getResearchDetail(Number(id)),
    [id]
  )

  async function handleMatch() {
    if (!supplierIds.trim()) {
      toast.error('サプライヤーIDを入力してください')
      return
    }
    setMatching(true)
    try {
      const res = await matchNetsea(Number(id), supplierIds.trim())
      setMatchResults(res.matches)
      toast.success(res.message)
      refetch()
    } catch (e: unknown) {
      toast.error((e as Error).message)
    } finally {
      setMatching(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-lg" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-[120px] rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-[300px] rounded-xl" />
      </div>
    )
  }

  if (error) return <ErrorState message={error} onRetry={refetch} />
  if (!data) return null

  const { session, top_items, price_dist, matches } = data
  const allMatches = matchResults.length > 0 ? matchResults : matches

  return (
    <div className="space-y-8">
      {/* ヘッダー */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/research')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          戻る
        </Button>
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <Search className="h-5 w-5 text-muted-foreground" />
            {session.keyword}
          </h1>
          <p className="text-xs text-muted-foreground">
            {new Date(session.searched_at).toLocaleString('ja-JP')} | サンプル {session.sample_size ?? 0}件
          </p>
        </div>
        <Badge
          variant="outline"
          className={
            session.status === 'completed'
              ? 'ml-auto bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
              : 'ml-auto bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
          }
        >
          {session.status}
        </Badge>
      </div>

      {/* KPIカード */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="総出品数"
          value={session.total_results?.toLocaleString() ?? '-'}
          icon={ShoppingCart}
        />
        <StatCard
          title="中央値価格"
          value={session.median_price_usd != null ? formatPrice(session.median_price_usd, 'USD') : '-'}
          icon={DollarSign}
        />
        <StatCard
          title="平均価格"
          value={session.avg_price_usd != null ? formatPrice(session.avg_price_usd, 'USD') : '-'}
          icon={TrendingUp}
        />
        <StatCard
          title="最安値"
          value={session.min_price_usd != null ? formatPrice(session.min_price_usd, 'USD') : '-'}
          icon={DollarSign}
          description={session.max_price_usd != null ? `最高値: ${formatPrice(session.max_price_usd, 'USD')}` : undefined}
        />
        <StatCard
          title="平均送料"
          value={session.avg_shipping_usd != null ? formatPrice(session.avg_shipping_usd, 'USD') : '-'}
          icon={Package}
        />
        <StatCard
          title="日本セラー数"
          value={session.japan_seller_count ?? 0}
          icon={Users}
          description={session.total_results ? `${((session.japan_seller_count ?? 0) / session.total_results * 100).toFixed(1)}%` : undefined}
        />
      </div>

      {/* 価格分布ヒストグラム */}
      {price_dist && price_dist.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              価格分布
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={price_dist}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="range"
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                />
                <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" />
                <ReTooltip
                  contentStyle={{ fontSize: 12 }}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(value: any) => [`${Number(value) || 0}件`, '出品数']}
                />
                <Bar
                  dataKey="count"
                  fill="hsl(var(--chart-1, 220 70% 50%))"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* トップ10商品 */}
      {top_items && top_items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              トップ商品
              <span className="ml-auto text-xs font-normal text-muted-foreground">{top_items.length}件</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead className="w-[50px]">#</TableHead>
                  <TableHead>タイトル</TableHead>
                  <TableHead className="text-right w-[100px]">価格</TableHead>
                  <TableHead className="text-right w-[100px]">送料</TableHead>
                  <TableHead className="w-[140px]">セラー</TableHead>
                  <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top_items.map((item, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="text-muted-foreground tabular-nums">{idx + 1}</TableCell>
                    <TableCell className="max-w-sm">
                      <p className="text-sm truncate">{item.title}</p>
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium">
                      {formatPrice(item.price, 'USD')}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {item.shipping != null ? formatPrice(item.shipping, 'USD') : 'Free'}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground truncate max-w-[140px]">
                      {item.seller || '-'}
                    </TableCell>
                    <TableCell>
                      {item.url && (
                        <a href={item.url} target="_blank" rel="noopener noreferrer">
                          <Button variant="ghost" size="sm" className="h-7 px-2">
                            <ExternalLink className="h-3 w-3" />
                          </Button>
                        </a>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* NETSEAマッチング */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4 text-muted-foreground" />
            NETSEAマッチング
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Supplier IDs（カンマ区切り）
              </Label>
              <Input
                value={supplierIds}
                onChange={(e) => setSupplierIds(e.target.value)}
                placeholder="79841,4387"
                className="h-10"
                disabled={matching}
              />
            </div>
            <Button onClick={handleMatch} disabled={matching || !supplierIds.trim()}>
              {matching ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  マッチング中...
                </>
              ) : (
                <>
                  <Search className="mr-1.5 h-3.5 w-3.5" />
                  NETSEA検索
                </>
              )}
            </Button>
          </div>

          {allMatches.length > 0 && (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead>商品名</TableHead>
                    <TableHead className="text-right w-[90px]">卸値</TableHead>
                    <TableHead className="text-right w-[90px]">推奨価格</TableHead>
                    <TableHead className="text-right w-[80px]">利益</TableHead>
                    <TableHead className="text-right w-[80px]">利益率</TableHead>
                    <TableHead className="text-right w-[80px]">スコア</TableHead>
                    <TableHead className="w-[80px]">DS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allMatches.map((m, idx) => (
                    <TableRow key={m.id || idx}>
                      <TableCell className="max-w-xs">
                        <p className="text-sm truncate">{m.netsea_name_ja || '-'}</p>
                        <p className="text-xs text-muted-foreground">{m.netsea_product_id}</p>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {m.wholesale_price_jpy != null ? formatPrice(m.wholesale_price_jpy) : '-'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {m.suggested_price_usd != null ? formatPrice(m.suggested_price_usd, 'USD') : '-'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {m.profit_usd != null ? formatPrice(m.profit_usd, 'USD') : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        {m.profit_margin != null ? (
                          <Badge
                            variant="outline"
                            className={
                              m.profit_margin >= 0.25
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
                                : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                            }
                          >
                            {formatMargin(m.profit_margin)}
                          </Badge>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-bold">
                        {m.total_score != null ? m.total_score.toFixed(1) : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-0.5">
                          {m.direct_send_flag === 'Y' && (
                            <Badge variant="outline" className="text-[10px] px-1 py-0">DS</Badge>
                          )}
                          {m.image_copy_flag === 'Y' && (
                            <Badge variant="outline" className="text-[10px] px-1 py-0">IMG</Badge>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
