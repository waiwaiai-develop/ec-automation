import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Package, List, ShoppingCart, DollarSign, BarChart3, TrendingUp, Activity, Star, CalendarClock } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip, ResponsiveContainer } from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StatCard } from '@/components/shared/StatCard'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { ErrorState } from '@/components/shared/ErrorState'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { SnsPlatformBadge, SnsStatusBadge } from '@/components/shared/Badges'
import { useApi } from '@/hooks/use-api'
import { getDashboard, getDashboardHistory, getPlatformStats, getProductsScoring, getSnsPosts } from '@/lib/api'
import { formatPrice } from '@/lib/formatters'

const categoryLabels: Record<string, string> = {
  tenugui: '手ぬぐい',
  furoshiki: '風呂敷',
  knife: '包丁',
  incense: 'お香',
  washi: '和紙',
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [historyDays, setHistoryDays] = useState(30)

  const { data, loading, error, refetch } = useApi(() => getDashboard(), [])
  const history = useApi(() => getDashboardHistory(historyDays), [historyDays])
  const platformStats = useApi(() => getPlatformStats(), [])
  const scoring = useApi(() => getProductsScoring(), [])
  const upcoming = useApi(() => getSnsPosts({ status: 'scheduled', limit: 10 }), [])
  const drafts = useApi(() => getSnsPosts({ status: 'draft', limit: 5 }), [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-[120px] rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-[300px] rounded-xl" />
      </div>
    )
  }

  if (error) {
    return <ErrorState message={error} onRetry={refetch} />
  }

  if (!data) return null

  const { stats, daily_summary } = data

  return (
    <div className="space-y-8">
      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="商品数" value={stats.products} icon={Package} />
        <StatCard
          title="出品数"
          value={stats.listings}
          icon={List}
          description={`Active: ${daily_summary.active_listings}`}
        />
        <StatCard
          title="注文数"
          value={stats.orders}
          icon={ShoppingCart}
          description={`Today: ${daily_summary.orders_count}`}
        />
        <StatCard
          title="本日売上"
          value={formatPrice(daily_summary.revenue_usd, 'USD')}
          icon={DollarSign}
          description={`Profit: ${formatPrice(daily_summary.profit_usd, 'USD')}`}
        />
      </div>

      {/* 売上・利益推移グラフ */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              売上・利益推移
            </CardTitle>
            <div className="flex items-center rounded-md border p-0.5">
              {[7, 30, 90].map((d) => (
                <Button
                  key={d}
                  variant={historyDays === d ? 'secondary' : 'ghost'}
                  size="sm"
                  className="h-7 px-2.5 text-xs"
                  onClick={() => setHistoryDays(d)}
                >
                  {d}日
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {history.loading ? (
            <Skeleton className="h-[250px] rounded-lg" />
          ) : history.data && history.data.history.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={history.data.history}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  tickFormatter={(v) => {
                    const d = new Date(v)
                    return `${d.getMonth() + 1}/${d.getDate()}`
                  }}
                />
                <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" />
                <ReTooltip
                  contentStyle={{ fontSize: 12 }}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(value: any, name: any) => [
                    `$${(Number(value) || 0).toFixed(2)}`,
                    name === 'revenue_usd' ? '売上' : '利益',
                  ]}
                  labelFormatter={(label) => {
                    const d = new Date(label as string)
                    return d.toLocaleDateString('ja-JP')
                  }}
                />
                <Line type="monotone" dataKey="revenue_usd" stroke="hsl(var(--chart-1, 220 70% 50%))" strokeWidth={2} dot={false} name="revenue_usd" />
                <Line type="monotone" dataKey="profit_usd" stroke="hsl(var(--chart-2, 160 60% 45%))" strokeWidth={2} dot={false} name="profit_usd" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center py-12 text-muted-foreground">
              <TrendingUp className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">注文データがありません</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* カテゴリ別商品数 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              カテゴリ別商品数
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.products_by_category && Object.keys(stats.products_by_category).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(stats.products_by_category)
                  .sort(([, a], [, b]) => b - a)
                  .map(([cat, count]) => {
                    const max = Math.max(...Object.values(stats.products_by_category))
                    const pct = max > 0 ? (count / max) * 100 : 0
                    const label = categoryLabels[cat] || cat
                    return (
                      <div
                        key={cat}
                        className="space-y-1.5 cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={() => navigate(`/products?category=${encodeURIComponent(cat)}`)}
                      >
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium hover:text-blue-600 transition-colors">{label}</span>
                          <span className="tabular-nums text-muted-foreground">{count}</span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-foreground/20 transition-all duration-700 ease-out"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
              </div>
            ) : (
              <div className="flex flex-col items-center py-8 text-muted-foreground">
                <Package className="h-8 w-8 mb-2 opacity-30" />
                <p className="text-sm">商品データがありません</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* プラットフォーム別統計 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4 text-muted-foreground" />
              プラットフォーム別統計
            </CardTitle>
          </CardHeader>
          <CardContent>
            {platformStats.loading ? (
              <Skeleton className="h-[120px] rounded-lg" />
            ) : platformStats.data && Object.keys(platformStats.data.platforms).length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead>Platform</TableHead>
                    <TableHead className="text-right">出品数</TableHead>
                    <TableHead className="text-right">Active</TableHead>
                    <TableHead className="text-right">注文</TableHead>
                    <TableHead className="text-right">売上</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(platformStats.data.platforms).map(([p, s]) => (
                    <TableRow key={p}>
                      <TableCell className="font-medium capitalize">{p}</TableCell>
                      <TableCell className="text-right tabular-nums">{s.listings_total}</TableCell>
                      <TableCell className="text-right tabular-nums">{s.listings_active}</TableCell>
                      <TableCell className="text-right tabular-nums">{s.orders}</TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {formatPrice(s.revenue_usd, 'USD')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="flex flex-col items-center py-8 text-muted-foreground">
                <Activity className="h-8 w-8 mb-2 opacity-30" />
                <p className="text-sm">出品データがありません</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 出品候補トップ */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Star className="h-4 w-4 text-muted-foreground" />
            出品候補（未出品・スコア順）
          </CardTitle>
        </CardHeader>
        <CardContent>
          {scoring.loading ? (
            <Skeleton className="h-[120px] rounded-lg" />
          ) : scoring.data && scoring.data.candidates.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>商品名</TableHead>
                  <TableHead>カテゴリ</TableHead>
                  <TableHead>卸値</TableHead>
                  <TableHead>スコア</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {scoring.data.candidates.slice(0, 5).map((c) => {
                  const colorClass = c.score >= 5 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
                    : c.score >= 3 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
                    : 'bg-muted text-muted-foreground'
                  return (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium text-sm max-w-xs truncate">
                        {c.name_ja}
                      </TableCell>
                      <TableCell>
                        {c.category ? (
                          <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs font-medium">
                            {categoryLabels[c.category] || c.category}
                          </span>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="tabular-nums">{formatPrice(c.wholesale_price_jpy)}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`text-xs px-1.5 py-0 ${colorClass}`}>
                          {c.score}/{c.max_score}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => navigate(`/products/${c.id}`)}
                        >
                          詳細
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center py-8 text-muted-foreground">
              <Star className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">未出品の商品がありません</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SNS投稿予定 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarClock className="h-4 w-4 text-muted-foreground" />
              SNS投稿予定
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => navigate('/sns')}
            >
              すべて見る
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {upcoming.loading ? (
            <Skeleton className="h-[120px] rounded-lg" />
          ) : (
            <>
              {/* 予約済み投稿 */}
              {upcoming.data && upcoming.data.posts.length > 0 ? (
                <div className="space-y-2">
                  {upcoming.data.posts.map((post) => {
                    const at = post.scheduled_at || post.created_at
                    const d = new Date(at)
                    const now = new Date()
                    const diffMs = d.getTime() - now.getTime()
                    const diffH = Math.floor(diffMs / (1000 * 60 * 60))
                    const diffD = Math.floor(diffH / 24)
                    let relativeTime = ''
                    if (diffMs < 0) {
                      relativeTime = '期限超過'
                    } else if (diffD > 0) {
                      relativeTime = `${diffD}日後`
                    } else if (diffH > 0) {
                      relativeTime = `${diffH}時間後`
                    } else {
                      const diffM = Math.max(0, Math.floor(diffMs / (1000 * 60)))
                      relativeTime = `${diffM}分後`
                    }

                    return (
                      <div
                        key={post.id}
                        className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/30 transition-colors cursor-pointer"
                        onClick={() => navigate('/sns')}
                      >
                        <SnsPlatformBadge platform={post.platform} />
                        <p className="flex-1 text-sm truncate min-w-0">{post.body}</p>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-xs text-muted-foreground tabular-nums">
                            {d.toLocaleString('ja-JP', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <Badge
                            variant="outline"
                            className={
                              diffMs < 0
                                ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                                : diffH < 1
                                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
                                  : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                            }
                          >
                            {relativeTime}
                          </Badge>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center py-6 text-muted-foreground">
                  <CalendarClock className="h-6 w-6 mb-2 opacity-30" />
                  <p className="text-sm">予約済みの投稿はありません</p>
                </div>
              )}

              {/* 下書き投稿（予約済みの下に表示） */}
              {drafts.data && drafts.data.posts.length > 0 && (
                <div className="mt-4 pt-3 border-t">
                  <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">下書き</p>
                  <div className="space-y-1.5">
                    {drafts.data.posts.map((post) => (
                      <div
                        key={post.id}
                        className="flex items-center gap-3 rounded-md px-3 py-2 hover:bg-muted/30 transition-colors cursor-pointer"
                        onClick={() => navigate('/sns')}
                      >
                        <SnsPlatformBadge platform={post.platform} />
                        <p className="flex-1 text-sm truncate min-w-0 text-muted-foreground">{post.body}</p>
                        <SnsStatusBadge status={post.status} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 日次サマリー */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            日次サマリー
            <span className="ml-auto text-xs font-normal text-muted-foreground">{daily_summary.date}</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="text-center rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground mb-1">注文数</p>
              <p className="text-3xl font-bold">{daily_summary.orders_count}</p>
            </div>
            <div className="text-center rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground mb-1">在庫変動</p>
              <p className="text-3xl font-bold">{daily_summary.stock_changes}</p>
            </div>
            <div className="text-center rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground mb-1">Active出品</p>
              <p className="text-3xl font-bold">{daily_summary.active_listings}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
