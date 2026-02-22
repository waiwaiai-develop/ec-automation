import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, Clock, TrendingUp, DollarSign, Users, ExternalLink } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useApi } from '@/hooks/use-api'
import { getResearchHistory, analyzeKeyword } from '@/lib/api'
import { formatPrice } from '@/lib/formatters'

export function ResearchPage() {
  const navigate = useNavigate()
  const [keyword, setKeyword] = useState('')
  const [limit, setLimit] = useState('50')
  const [analyzing, setAnalyzing] = useState(false)
  const [filterKeyword, setFilterKeyword] = useState('')

  const history = useApi(
    () => getResearchHistory({ keyword: filterKeyword || undefined, limit: 50 }),
    [filterKeyword],
    { debounceMs: 300 }
  )

  async function handleAnalyze() {
    if (!keyword.trim()) {
      toast.error('キーワードを入力してください')
      return
    }
    setAnalyzing(true)
    try {
      const res = await analyzeKeyword(keyword.trim(), Number(limit))
      toast.success(res.message)
      navigate(`/research/${res.session.id}`)
    } catch (e: unknown) {
      toast.error((e as Error).message)
    } finally {
      setAnalyzing(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleAnalyze()
  }

  return (
    <div className="space-y-8">
      {/* リサーチ実行カード */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4 text-muted-foreground" />
            eBay需要分析
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-[1fr_150px]">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Keyword</Label>
              <Input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="例: japanese tenugui, furoshiki, incense stick"
                className="h-10"
                disabled={analyzing}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Sample Size</Label>
              <Select value={limit} onValueChange={setLimit}>
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20件</SelectItem>
                  <SelectItem value="50">50件</SelectItem>
                  <SelectItem value="100">100件</SelectItem>
                  <SelectItem value="200">200件</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2 border-t">
            <Button onClick={handleAnalyze} disabled={analyzing || !keyword.trim()}>
              {analyzing ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <Search className="mr-1.5 h-3.5 w-3.5" />
                  eBay需要調査
                </>
              )}
            </Button>
            <p className="text-xs text-muted-foreground ml-2">
              eBay Browse APIでキーワードの需要・価格帯・競合を分析します
            </p>
          </div>
        </CardContent>
      </Card>

      {/* リサーチ履歴 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4 text-muted-foreground" />
              リサーチ履歴
            </CardTitle>
            <Input
              value={filterKeyword}
              onChange={(e) => setFilterKeyword(e.target.value)}
              placeholder="キーワードで絞り込み..."
              className="h-8 w-[220px] text-xs"
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {history.loading ? (
            <div className="p-6 space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 rounded-lg" />
              ))}
            </div>
          ) : history.data && history.data.sessions.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>キーワード</TableHead>
                  <TableHead className="text-right">
                    <span className="inline-flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />出品数
                    </span>
                  </TableHead>
                  <TableHead className="text-right">
                    <span className="inline-flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />中央値
                    </span>
                  </TableHead>
                  <TableHead className="text-right">
                    <span className="inline-flex items-center gap-1">
                      <Users className="h-3 w-3" />日本セラー
                    </span>
                  </TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  <TableHead className="w-[140px]">日時</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.data.sessions.map((s) => (
                  <TableRow
                    key={s.id}
                    className="cursor-pointer hover:bg-muted/30"
                    onClick={() => navigate(`/research/${s.id}`)}
                  >
                    <TableCell className="font-medium">{s.keyword}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.total_results?.toLocaleString() ?? '-'}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.median_price_usd != null ? formatPrice(s.median_price_usd, 'USD') : '-'}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.japan_seller_count ?? '-'}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          s.status === 'completed'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
                            : s.status === 'failed'
                              ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                              : 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
                        }
                      >
                        {s.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground tabular-nums">
                      {new Date(s.searched_at).toLocaleString('ja-JP')}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="h-7 px-2">
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center py-12 text-muted-foreground">
              <Search className="h-6 w-6 opacity-30 mb-3" />
              <p className="text-sm font-medium">リサーチ履歴がありません</p>
              <p className="text-xs mt-1">上のフォームからキーワードを入力して分析を始めましょう</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
