import { useState, useMemo } from 'react'
import { Sparkles, Send, Trash2, Clock, MessageSquare, Hash, Calendar, List, CalendarDays } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
import { SnsPlatformBadge, SnsStatusBadge, XIcon, InstagramIcon, ThreadsIcon } from '@/components/shared/Badges'
import { MonthCalendar } from '@/components/shared/MonthCalendar'
import { useApi } from '@/hooks/use-api'
import {
  getSnsPosts,
  getProducts,
  createSnsPost,
  generateSnsBody,
  publishSnsPost,
  deleteSnsPost,
} from '@/lib/api'
import type { SnsPlatform, SnsPostStatus, SnsPost } from '@/types'

const CHAR_LIMITS: Record<SnsPlatform, number> = {
  twitter: 280,
  instagram: 2200,
  threads: 500,
}

type ViewMode = 'list' | 'calendar'

export function SnsPage() {
  const [platform, setPlatform] = useState<SnsPlatform>('twitter')
  const [productId, setProductId] = useState<string>('')
  const [body, setBody] = useState('')
  const [hashtags, setHashtags] = useState('')
  const [scheduledAt, setScheduledAt] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [generating, setGenerating] = useState(false)

  const [filterPlatform, setFilterPlatform] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')

  // ビュー切替
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const now = new Date()
  const [calYear, setCalYear] = useState(now.getFullYear())
  const [calMonth, setCalMonth] = useState(now.getMonth())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const postsApi = useApi(
    () => getSnsPosts({
      platform: filterPlatform !== 'all' ? filterPlatform as SnsPlatform : undefined,
      status: filterStatus !== 'all' ? filterStatus as SnsPostStatus : undefined,
      limit: 100,
    }),
    [filterPlatform, filterStatus]
  )

  // カレンダー用: 表示月の投稿を取得
  const calDateFrom = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-01`
  const nextMonth = calMonth === 11 ? 0 : calMonth + 1
  const nextYear = calMonth === 11 ? calYear + 1 : calYear
  const calDateTo = `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-01`

  const calPostsApi = useApi(
    () => getSnsPosts({
      platform: filterPlatform !== 'all' ? filterPlatform as SnsPlatform : undefined,
      date_from: calDateFrom,
      date_to: calDateTo,
      limit: 200,
    }),
    [filterPlatform, calYear, calMonth]
  )

  // 選択日の投稿をフィルタ
  const selectedDayPosts = useMemo<SnsPost[]>(() => {
    if (!selectedDate || !calPostsApi.data) return []
    return calPostsApi.data.posts.filter((p) => {
      const at = p.scheduled_at || p.created_at
      return at && at.startsWith(selectedDate)
    })
  }, [selectedDate, calPostsApi.data])

  const productsApi = useApi(() => getProducts({ limit: 200 }), [])

  const charLimit = CHAR_LIMITS[platform]
  const charRatio = body.length / charLimit

  async function handleGenerate() {
    if (!productId || productId === 'none') {
      toast.error('商品を選択してください')
      return
    }
    setGenerating(true)
    try {
      const res = await generateSnsBody({ product_id: Number(productId), platform })
      setBody(res.body)
      setHashtags(res.hashtags)
      toast.success('投稿文を生成しました')
    } catch (e: unknown) {
      toast.error((e as Error).message)
    } finally {
      setGenerating(false)
    }
  }

  async function handleSave() {
    if (!body.trim()) { toast.error('本文を入力してください'); return }
    setSubmitting(true)
    try {
      await createSnsPost({
        product_id: productId && productId !== 'none' ? Number(productId) : null,
        platform, body,
        hashtags: hashtags || undefined,
        scheduled_at: scheduledAt || null,
        status: scheduledAt ? 'scheduled' : 'draft',
      })
      toast.success('投稿を保存しました')
      setBody(''); setHashtags(''); setScheduledAt('')
      postsApi.refetch()
      calPostsApi.refetch()
    } catch (e: unknown) {
      toast.error((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handlePost() {
    if (!body.trim()) { toast.error('本文を入力してください'); return }
    setSubmitting(true)
    try {
      const res = await createSnsPost({
        product_id: productId && productId !== 'none' ? Number(productId) : null,
        platform, body,
        hashtags: hashtags || undefined,
        status: 'draft',
      })
      await publishSnsPost(res.post.id)
      toast.success('投稿しました')
      setBody(''); setHashtags(''); setScheduledAt('')
      postsApi.refetch()
      calPostsApi.refetch()
    } catch (e: unknown) {
      toast.error((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handlePublish(postId: number) {
    try {
      await publishSnsPost(postId)
      toast.success('投稿しました')
      postsApi.refetch()
      calPostsApi.refetch()
    } catch (e: unknown) {
      toast.error((e as Error).message)
    }
  }

  async function handleDelete(postId: number) {
    try {
      await deleteSnsPost(postId)
      toast.success('削除しました')
      postsApi.refetch()
      calPostsApi.refetch()
    } catch (e: unknown) {
      toast.error((e as Error).message)
    }
  }

  function handleMonthChange(y: number, m: number) {
    setCalYear(y)
    setCalMonth(m)
    setSelectedDate(null)
  }

  return (
    <div className="space-y-8">
      {/* 新規SNS投稿カード */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            新規SNS投稿
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Platform</Label>
              <Select value={platform} onValueChange={(v) => setPlatform(v as SnsPlatform)}>
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="twitter">
                    <span className="inline-flex items-center gap-1.5">
                      <XIcon className="h-3.5 w-3.5" />
                      X (Twitter)
                    </span>
                  </SelectItem>
                  <SelectItem value="instagram">
                    <span className="inline-flex items-center gap-1.5">
                      <InstagramIcon className="h-3.5 w-3.5" />
                      Instagram
                    </span>
                  </SelectItem>
                  <SelectItem value="threads">
                    <span className="inline-flex items-center gap-1.5">
                      <ThreadsIcon className="h-3.5 w-3.5" />
                      Threads
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Product</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder="商品を選択..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- なし --</SelectItem>
                  {productsApi.data?.products.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.name_ja}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Body</Label>
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
              maxLength={charLimit}
              placeholder="投稿本文を入力..."
              className="resize-none"
            />
            <div className="flex items-center justify-between">
              <div className="flex-1 mr-4">
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      charRatio > 0.9 ? 'bg-red-500' : charRatio > 0.7 ? 'bg-amber-500' : 'bg-foreground/20'
                    }`}
                    style={{ width: `${Math.min(charRatio * 100, 100)}%` }}
                  />
                </div>
              </div>
              <span className={`text-xs tabular-nums font-medium ${
                charRatio > 0.9 ? 'text-red-500' : 'text-muted-foreground'
              }`}>
                {body.length}/{charLimit}
              </span>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <Hash className="h-3 w-3" />
                Hashtags
              </Label>
              <Input
                value={hashtags}
                onChange={(e) => setHashtags(e.target.value)}
                placeholder="#japanese #tenugui #madeinjapan"
                className="h-10"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <Calendar className="h-3 w-3" />
                Schedule
              </Label>
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                className="h-10"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={generating || !productId || productId === 'none'}
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              {generating ? 'AI生成中...' : 'AI生成'}
            </Button>
            <div className="flex-1" />
            <Button variant="outline" size="sm" onClick={handleSave} disabled={submitting}>
              {submitting ? '保存中...' : '下書き保存'}
            </Button>
            <Button size="sm" onClick={handlePost} disabled={submitting}>
              <Send className="mr-1.5 h-3.5 w-3.5" />
              {submitting ? '投稿中...' : '今すぐ投稿'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* フィルター */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-muted-foreground">Filter:</span>
        <Select value={filterPlatform} onValueChange={setFilterPlatform}>
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="Platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Platforms</SelectItem>
            <SelectItem value="twitter">
              <span className="inline-flex items-center gap-1.5">
                <XIcon className="h-3 w-3" /> X
              </span>
            </SelectItem>
            <SelectItem value="instagram">
              <span className="inline-flex items-center gap-1.5">
                <InstagramIcon className="h-3 w-3" /> Instagram
              </span>
            </SelectItem>
            <SelectItem value="threads">
              <span className="inline-flex items-center gap-1.5">
                <ThreadsIcon className="h-3 w-3" /> Threads
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">下書き</SelectItem>
            <SelectItem value="scheduled">予約済み</SelectItem>
            <SelectItem value="posted">投稿済み</SelectItem>
            <SelectItem value="failed">失敗</SelectItem>
          </SelectContent>
        </Select>
        {postsApi.data && (
          <span className="ml-auto text-xs text-muted-foreground tabular-nums">
            {postsApi.data.total} posts
          </span>
        )}
      </div>

      {/* 投稿履歴カード */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4 text-muted-foreground" />
              投稿履歴
            </CardTitle>
            {/* ビュー切替ボタン */}
            <div className="flex items-center rounded-md border p-0.5">
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7 px-2.5 text-xs"
                onClick={() => setViewMode('list')}
              >
                <List className="h-3.5 w-3.5 mr-1" />
                リスト
              </Button>
              <Button
                variant={viewMode === 'calendar' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7 px-2.5 text-xs"
                onClick={() => setViewMode('calendar')}
              >
                <CalendarDays className="h-3.5 w-3.5 mr-1" />
                カレンダー
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className={viewMode === 'list' ? 'p-0' : ''}>
          {viewMode === 'list' ? (
            /* --- リストビュー --- */
            <>
              {postsApi.loading ? (
                <div className="p-6 space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-12 rounded-lg" />
                  ))}
                </div>
              ) : postsApi.data && postsApi.data.posts.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30">
                      <TableHead className="w-[120px]">Platform</TableHead>
                      <TableHead>本文</TableHead>
                      <TableHead className="w-[100px]">Status</TableHead>
                      <TableHead className="w-[160px]">日時</TableHead>
                      <TableHead className="w-[120px] text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {postsApi.data.posts.map((post) => (
                      <TableRow key={post.id} className="group hover:bg-muted/30">
                        <TableCell>
                          <SnsPlatformBadge platform={post.platform} />
                        </TableCell>
                        <TableCell>
                          <p className="max-w-sm truncate text-sm">{post.body}</p>
                          {post.hashtags && (
                            <p className="text-xs text-muted-foreground truncate mt-0.5">{post.hashtags}</p>
                          )}
                        </TableCell>
                        <TableCell>
                          <SnsStatusBadge status={post.status} />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground tabular-nums">
                          {post.posted_at
                            ? new Date(post.posted_at).toLocaleString('ja-JP')
                            : post.scheduled_at
                              ? new Date(post.scheduled_at).toLocaleString('ja-JP')
                              : new Date(post.created_at).toLocaleString('ja-JP')}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {(post.status === 'draft' || post.status === 'scheduled') && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 px-2"
                                onClick={() => handlePublish(post.id)}
                              >
                                <Send className="h-3 w-3 mr-1" />
                                投稿
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2 text-destructive hover:text-destructive"
                              onClick={() => handleDelete(post.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="flex flex-col items-center py-12 text-muted-foreground">
                  <MessageSquare className="h-6 w-6 opacity-30 mb-3" />
                  <p className="text-sm font-medium">投稿履歴がありません</p>
                  <p className="text-xs mt-1">上のフォームから最初の投稿を作成しましょう</p>
                </div>
              )}
            </>
          ) : (
            /* --- カレンダービュー --- */
            <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
              {/* 左: カレンダーグリッド */}
              <div>
                {calPostsApi.loading ? (
                  <Skeleton className="h-64 rounded-lg" />
                ) : (
                  <MonthCalendar
                    year={calYear}
                    month={calMonth}
                    posts={calPostsApi.data?.posts ?? []}
                    selectedDate={selectedDate}
                    onDateSelect={setSelectedDate}
                    onMonthChange={handleMonthChange}
                  />
                )}
              </div>

              {/* 右: 選択日の投稿リスト */}
              <div className="min-h-[200px]">
                {selectedDate ? (
                  <>
                    <h3 className="text-sm font-semibold mb-3">
                      {new Date(selectedDate + 'T00:00:00').toLocaleDateString('ja-JP', {
                        year: 'numeric', month: 'long', day: 'numeric', weekday: 'short',
                      })}
                    </h3>
                    {selectedDayPosts.length > 0 ? (
                      <div className="space-y-2">
                        {selectedDayPosts.map((post) => (
                          <CalendarPostCard
                            key={post.id}
                            post={post}
                            onPublish={handlePublish}
                            onDelete={handleDelete}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center py-10 text-muted-foreground">
                        <Calendar className="h-5 w-5 opacity-30 mb-2" />
                        <p className="text-sm">この日の投稿はありません</p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center py-10 text-muted-foreground">
                    <CalendarDays className="h-5 w-5 opacity-30 mb-2" />
                    <p className="text-sm">日付をクリックして投稿を表示</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

/** カレンダービュー用の投稿カード */
function CalendarPostCard({
  post,
  onPublish,
  onDelete,
}: {
  post: SnsPost
  onPublish: (id: number) => void
  onDelete: (id: number) => void
}) {
  const time = post.scheduled_at || post.created_at
  const timeStr = time ? new Date(time).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }) : ''

  return (
    <div className="group flex items-start gap-3 rounded-lg border p-3 hover:bg-muted/30 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <SnsPlatformBadge platform={post.platform} />
          <SnsStatusBadge status={post.status} />
          {timeStr && (
            <span className="text-[11px] text-muted-foreground tabular-nums">{timeStr}</span>
          )}
        </div>
        <p className="text-sm truncate">{post.body}</p>
        {post.hashtags && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">{post.hashtags}</p>
        )}
      </div>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        {(post.status === 'draft' || post.status === 'scheduled') && (
          <Button size="sm" variant="outline" className="h-7 px-2" onClick={() => onPublish(post.id)}>
            <Send className="h-3 w-3 mr-1" />
            投稿
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="h-7 px-2 text-destructive hover:text-destructive"
          onClick={() => onDelete(post.id)}
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}
