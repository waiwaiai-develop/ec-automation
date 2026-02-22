import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Sparkles, AlertTriangle, CheckCircle, ExternalLink, Send, Share2, DollarSign, Globe, ShoppingBag, Save, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Slider } from '@/components/ui/slider'
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { StockBadge, PlatformBadge, StatusBadge, XIcon, InstagramIcon, ThreadsIcon } from '@/components/shared/Badges'
import { ErrorState } from '@/components/shared/ErrorState'
import { useApi } from '@/hooks/use-api'
import {
  getProductDetail,
  updateProduct,
  generateListing,
  generateListingJa,
  banCheck,
  listOnEbay,
  listOnBase,
  generateSnsBody,
  createSnsPost,
  publishSnsPost,
  calculateProfit,
} from '@/lib/api'
import { formatPrice, formatMargin } from '@/lib/formatters'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ProfitCalc, SnsPlatform } from '@/types'

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const productId = Number(id)
  const { data, loading, error, refetch } = useApi(
    () => getProductDetail(productId),
    [productId]
  )

  const [titleEn, setTitleEn] = useState('')
  const [descEn, setDescEn] = useState('')
  const [tagsEn, setTagsEn] = useState('')
  const [priceUsd, setPriceUsd] = useState('25.00')

  const [titleJa, setTitleJa] = useState('')
  const [descJa, setDescJa] = useState('')
  const [priceJpy, setPriceJpy] = useState('')

  const [banResult, setBanResult] = useState<{
    passed: boolean
    issues: string[]
    excluded_countries: string[]
  } | null>(null)
  const [banLoading, setBanLoading] = useState(false)
  const [banError, setBanError] = useState<string | null>(null)

  // SNS
  const [snsPlatform, setSnsPlatform] = useState<SnsPlatform>('twitter')
  const [snsBody, setSnsBody] = useState('')
  const [snsHashtags, setSnsHashtags] = useState('')
  const [snsGenLoading, setSnsGenLoading] = useState(false)
  const [snsPosting, setSnsPosting] = useState(false)

  const snsCharLimits: Record<SnsPlatform, number> = {
    twitter: 280, instagram: 2200, threads: 500,
  }
  const snsCharLimit = snsCharLimits[snsPlatform]
  const snsCharRatio = snsBody.length / snsCharLimit

  const [genLoading, setGenLoading] = useState(false)
  const [genJaLoading, setGenJaLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [listingEbay, setListingEbay] = useState(false)
  const [listingBase, setListingBase] = useState(false)

  // 未保存検知
  const initialRef = useRef<{ titleEn: string; descEn: string; titleJa: string; descJa: string } | null>(null)
  const isDirty = initialRef.current && (
    titleEn !== initialRef.current.titleEn ||
    descEn !== initialRef.current.descEn ||
    titleJa !== initialRef.current.titleJa ||
    descJa !== initialRef.current.descJa
  )

  // 画像ライトボックス
  const [lightboxImg, setLightboxImg] = useState<string | null>(null)

  // 利益シミュレーション
  const [simPrice, setSimPrice] = useState(25)
  const [simPlatform, setSimPlatform] = useState('ebay')
  const [simResult, setSimResult] = useState<ProfitCalc | null>(null)
  const [simLoading, setSimLoading] = useState(false)

  const runSimulation = useCallback(async (price: number, platform: string) => {
    setSimLoading(true)
    try {
      const res = await calculateProfit(productId, price, platform)
      setSimResult(res)
    } catch {
      // 利益計算エラーは無視（卸値未設定等）
    } finally {
      setSimLoading(false)
    }
  }, [productId])

  useEffect(() => {
    if (!data) return
    const p = data.product
    setTitleEn(p.name_en || '')
    setDescEn(p.description_en || '')
    setTitleJa(p.name_ja || '')
    setDescJa(p.description_ja || '')
    const wp = p.wholesale_price_jpy
    if (wp) setPriceJpy(String(Math.round(wp * 2.5)))

    initialRef.current = {
      titleEn: p.name_en || '',
      descEn: p.description_en || '',
      titleJa: p.name_ja || '',
      descJa: p.description_ja || '',
    }

    // BANチェック
    setBanLoading(true)
    setBanError(null)
    banCheck(productId)
      .then(setBanResult)
      .catch((e: Error) => setBanError(e.message))
      .finally(() => setBanLoading(false))

    // 利益シミュレーション初期値
    runSimulation(25, 'ebay')
  }, [data, productId, runSimulation])

  // ページ離脱防止
  useEffect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      if (isDirty) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-40 rounded-lg" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[300px] rounded-xl" />
          <Skeleton className="h-[300px] rounded-xl" />
        </div>
      </div>
    )
  }
  if (error || !data) {
    return (
      <div className="space-y-4">
        <Link to="/products" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" /> 商品一覧に戻る
        </Link>
        <ErrorState message={error || '商品が見つかりません'} onRetry={refetch} />
      </div>
    )
  }

  const { product, images, profit_info, listings } = data

  // ステップ完了状態
  const stepBan = banResult !== null
  const stepBanPassed = banResult?.passed ?? false
  const stepAi = !!titleEn && !!descEn
  const stepListed = listings.length > 0

  async function handleGenerateEn() {
    setGenLoading(true)
    try {
      const res = await generateListing(productId)
      setTitleEn(res.title); setDescEn(res.description)
      setTagsEn(res.tags.join(', '))
      toast.success('英語リスティングを生成しました')
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setGenLoading(false) }
  }

  async function handleGenerateJa() {
    setGenJaLoading(true)
    try {
      const res = await generateListingJa(productId)
      setTitleJa(res.title_ja); setDescJa(res.description_ja)
      toast.success('日本語リスティングを生成しました')
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setGenJaLoading(false) }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await updateProduct(productId, {
        name_en: titleEn, description_en: descEn,
        name_ja: titleJa, description_ja: descJa,
      })
      initialRef.current = { titleEn, descEn, titleJa, descJa }
      toast.success('保存しました')
      refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setSaving(false) }
  }

  async function handleListEbay() {
    if (!titleEn || !descEn) { toast.error('英語タイトルと説明が必要です'); return }
    setListingEbay(true)
    try {
      const res = await listOnEbay(productId, {
        title_en: titleEn, description_en: descEn,
        price_usd: parseFloat(priceUsd),
        tags: tagsEn.split(',').map(t => t.trim()).filter(Boolean),
      })
      toast.success(res.message); refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setListingEbay(false) }
  }

  async function handleSnsGenerate() {
    setSnsGenLoading(true)
    try {
      const res = await generateSnsBody({ product_id: productId, platform: snsPlatform })
      setSnsBody(res.body); setSnsHashtags(res.hashtags)
      toast.success('SNS投稿文を生成しました')
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setSnsGenLoading(false) }
  }

  async function handleSnsPost() {
    if (!snsBody.trim()) { toast.error('本文を入力してください'); return }
    setSnsPosting(true)
    try {
      const res = await createSnsPost({
        product_id: productId, platform: snsPlatform,
        body: snsBody, hashtags: snsHashtags || undefined, status: 'draft',
      })
      await publishSnsPost(res.post.id)
      toast.success('SNS投稿しました')
      setSnsBody(''); setSnsHashtags('')
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setSnsPosting(false) }
  }

  async function handleListBase() {
    if (!priceJpy) { toast.error('販売価格(JPY)が必要です'); return }
    setListingBase(true)
    try {
      const res = await listOnBase(productId, {
        price_jpy: parseInt(priceJpy), title_ja: titleJa, description_ja: descJa,
      })
      toast.success(res.message); refetch()
    } catch (e: unknown) { toast.error((e as Error).message) }
    finally { setListingBase(false) }
  }

  return (
    <div className="space-y-6 pb-20">
      <Link to="/products" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors group">
        <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" /> 商品一覧に戻る
      </Link>

      {/* 出品ワークフロー ステップ */}
      <div className="flex items-center gap-2">
        <StepBadge label="1. BANチェック" done={stepBan && stepBanPassed} error={stepBan && !stepBanPassed} loading={banLoading} />
        <div className="h-px w-6 bg-border" />
        <StepBadge label="2. AI生成" done={stepAi} />
        <div className="h-px w-6 bg-border" />
        <StepBadge label="3. 出品" done={stepListed} />
      </div>

      {/* 商品情報 */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            {images.length > 0 ? (
              <div className="grid grid-cols-2 gap-1 p-2">
                {images.map((url, i) => (
                  <img
                    key={i}
                    src={url}
                    alt={`${product.name_ja} ${i + 1}`}
                    className="rounded-lg object-cover w-full aspect-square cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={() => setLightboxImg(url)}
                  />
                ))}
              </div>
            ) : (
              <div className="flex h-64 items-center justify-center bg-muted/30 text-muted-foreground">
                <ShoppingBag className="h-12 w-12 opacity-20" />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-lg leading-tight">{product.name_ja}</CardTitle>
              <StockBadge status={product.stock_status} />
            </div>
            {product.product_url && (
              <a
                href={product.product_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                NETSEA商品ページ
              </a>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-muted/50 p-2.5">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-0.5">Category</p>
                <p className="font-medium">{product.category || '-'}</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-2.5">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-0.5">Weight</p>
                <p className="font-medium">{product.weight_g != null ? `${product.weight_g}g` : '不明'}</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-2.5">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-0.5">卸値</p>
                <p className="font-bold">{formatPrice(product.wholesale_price_jpy)}</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-2.5">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-0.5">参考価格</p>
                <p className="font-medium">{formatPrice(product.reference_price_jpy)}</p>
              </div>
            </div>
            <div className="text-xs text-muted-foreground">
              <span className="font-medium">{product.supplier}</span>
              {product.shop_name && <span> / {product.shop_name}</span>}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 画像ライトボックス */}
      <Dialog open={!!lightboxImg} onOpenChange={(open) => !open && setLightboxImg(null)}>
        <DialogContent className="max-w-3xl p-2">
          {lightboxImg && (
            <img src={lightboxImg} alt="" className="w-full h-auto rounded-lg" />
          )}
        </DialogContent>
      </Dialog>

      {/* BANチェック結果 */}
      {banLoading ? (
        <Card className="border-muted">
          <CardContent className="flex items-center gap-3 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">BANチェック中...</p>
          </CardContent>
        </Card>
      ) : banError ? (
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="flex items-start gap-3 p-4">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-sm text-red-700 dark:text-red-400">BANチェックエラー</p>
              <p className="text-sm text-muted-foreground mt-1">{banError}</p>
            </div>
          </CardContent>
        </Card>
      ) : banResult && (
        <Card className={banResult.passed
          ? 'border-emerald-200 dark:border-emerald-800'
          : 'border-red-200 dark:border-red-800'
        }>
          <CardContent className="flex items-start gap-3 p-4">
            {banResult.passed ? (
              <CheckCircle className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            )}
            <div>
              <p className={`font-semibold text-sm ${banResult.passed ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}`}>
                {banResult.passed ? 'BANチェック通過' : 'BANリスク検出'}
              </p>
              {banResult.issues.length > 0 && (
                <ul className="mt-1.5 space-y-1 text-sm text-muted-foreground">
                  {banResult.issues.map((issue, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="h-1 w-1 rounded-full bg-current" />
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
              {banResult.excluded_countries.length > 0 && (
                <div className="mt-2 flex items-center gap-1.5">
                  <Globe className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">除外国:</span>
                  {banResult.excluded_countries.map(c => (
                    <Badge key={c} variant="outline" className="text-xs px-1.5 py-0">{c}</Badge>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 英語リスティング */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4 text-muted-foreground" />
            English Listing (eBay)
          </CardTitle>
          <Button
            variant="outline" size="sm" onClick={handleGenerateEn} disabled={genLoading}
          >
            <Sparkles className="mr-1 h-3 w-3" />
            {genLoading ? 'AI生成中...' : 'AI生成'}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Title (80)</Label>
            <Input value={titleEn} onChange={(e) => setTitleEn(e.target.value)} maxLength={80} placeholder="English title..." />
            <div className="h-1 rounded-full bg-muted mt-1 overflow-hidden">
              <div className={`h-full rounded-full transition-all ${titleEn.length > 70 ? 'bg-amber-500' : 'bg-foreground/20'}`} style={{ width: `${(titleEn.length / 80) * 100}%` }} />
            </div>
          </div>
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Description</Label>
            <Textarea value={descEn} onChange={(e) => setDescEn(e.target.value)} rows={5} placeholder="Product description..." className="resize-none" />
          </div>
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">SEO Tags</Label>
            <Input value={tagsEn} onChange={(e) => setTagsEn(e.target.value)} placeholder="tenugui, japanese, cotton..." />
          </div>
        </CardContent>
      </Card>

      {/* 日本語リスティング */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
            日本語リスティング (BASE)
          </CardTitle>
          <Button
            variant="outline" size="sm" onClick={handleGenerateJa} disabled={genJaLoading}
          >
            <Sparkles className="mr-1 h-3 w-3" />
            {genJaLoading ? 'AI生成中...' : 'AI生成'}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Title (50)</Label>
            <Input value={titleJa} onChange={(e) => setTitleJa(e.target.value)} maxLength={50} placeholder="日本語タイトル..." />
            <div className="h-1 rounded-full bg-muted mt-1 overflow-hidden">
              <div className={`h-full rounded-full transition-all ${titleJa.length > 40 ? 'bg-amber-500' : 'bg-foreground/20'}`} style={{ width: `${(titleJa.length / 50) * 100}%` }} />
            </div>
          </div>
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Description</Label>
            <Textarea value={descJa} onChange={(e) => setDescJa(e.target.value)} rows={5} placeholder="商品説明..." className="resize-none" />
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* 利益シミュレーション（インタラクティブ） */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            利益シミュレーション
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                販売価格: ${simPrice}
              </Label>
              <Slider
                value={[simPrice]}
                onValueChange={([v]) => {
                  setSimPrice(v)
                  runSimulation(v, simPlatform)
                }}
                min={5}
                max={100}
                step={1}
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>$5</span>
                <span>$100</span>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">プラットフォーム</Label>
              <Select value={simPlatform} onValueChange={(v) => { setSimPlatform(v); runSimulation(simPrice, v) }}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ebay">eBay</SelectItem>
                  <SelectItem value="base">BASE</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {simLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" /> 計算中...
            </div>
          ) : simResult ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-lg border p-3 text-center">
                <p className="text-[10px] font-medium text-muted-foreground uppercase mb-1">卸値(USD)</p>
                <p className="text-lg font-bold tabular-nums">{formatPrice(simResult.wholesale_usd, 'USD')}</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-[10px] font-medium text-muted-foreground uppercase mb-1">送料</p>
                <p className="text-lg font-bold tabular-nums">{formatPrice(simResult.shipping_usd, 'USD')}</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-[10px] font-medium text-muted-foreground uppercase mb-1">手数料</p>
                <p className="text-lg font-bold tabular-nums">{formatPrice(simResult.platform_fees_usd, 'USD')}</p>
              </div>
              <div className={`rounded-lg border-2 p-3 text-center ${
                simResult.profit_margin >= 0.25
                  ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950'
                  : simResult.profitable
                    ? 'border-amber-500 bg-amber-50 dark:bg-amber-950'
                    : 'border-red-500 bg-red-50 dark:bg-red-950'
              }`}>
                <p className="text-[10px] font-medium text-muted-foreground uppercase mb-1">利益</p>
                <p className={`text-lg font-bold tabular-nums ${
                  simResult.profitable ? 'text-emerald-600' : 'text-red-600'
                }`}>
                  {formatPrice(simResult.profit_usd, 'USD')}
                </p>
                <p className={`text-xs font-semibold ${
                  simResult.profit_margin >= 0.25 ? 'text-emerald-600'
                  : simResult.profitable ? 'text-amber-600'
                  : 'text-red-600'
                }`}>
                  {formatMargin(simResult.profit_margin)}
                  {simResult.profit_margin < 0.25 && simResult.profitable && ' (25%未満)'}
                </p>
              </div>
            </div>
          ) : null}

          {/* 固定価格テーブル（参考） */}
          {profit_info && profit_info.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                固定価格テーブル（$15/$20/$25/$30）
              </summary>
              <Table className="mt-2">
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead>販売価格</TableHead>
                    <TableHead>卸値(USD)</TableHead>
                    <TableHead>送料</TableHead>
                    <TableHead>手数料</TableHead>
                    <TableHead>利益</TableHead>
                    <TableHead>利益率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {profit_info.map((p: ProfitCalc, i: number) => (
                    <TableRow key={i}>
                      <TableCell className="font-semibold">{formatPrice(p.sale_usd, 'USD')}</TableCell>
                      <TableCell>{formatPrice(p.wholesale_usd, 'USD')}</TableCell>
                      <TableCell>{formatPrice(p.shipping_usd, 'USD')}</TableCell>
                      <TableCell>{formatPrice(p.platform_fees_usd, 'USD')}</TableCell>
                      <TableCell className={`font-bold ${p.profitable ? 'text-emerald-600' : 'text-red-600'}`}>
                        {formatPrice(p.profit_usd, 'USD')}
                      </TableCell>
                      <TableCell>
                        <span className={`text-xs font-semibold ${p.profitable ? 'text-emerald-600' : 'text-red-600'}`}>
                          {formatMargin(p.profit_margin)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </details>
          )}
        </CardContent>
      </Card>

      {/* プラットフォーム出品 */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <PlatformBadge platform="ebay" />
              出品
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Price (USD)</Label>
              <Input type="number" step="0.01" value={priceUsd} onChange={(e) => setPriceUsd(e.target.value)} />
            </div>
            <Button onClick={handleListEbay} disabled={listingEbay} className="w-full">
              <ExternalLink className="mr-2 h-4 w-4" />
              {listingEbay ? '出品中...' : 'eBayに出品'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <PlatformBadge platform="base" />
              出品
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Price (JPY)</Label>
              <Input type="number" value={priceJpy} onChange={(e) => setPriceJpy(e.target.value)} />
            </div>
            <Button onClick={handleListBase} disabled={listingBase} className="w-full">
              <ExternalLink className="mr-2 h-4 w-4" />
              {listingBase ? '出品中...' : 'BASEに出品'}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* 関連リスティング */}
      {listings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
              関連リスティング
              <Badge variant="outline" className="ml-auto text-xs">{listings.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Platform</TableHead>
                  <TableHead>タイトル</TableHead>
                  <TableHead>価格</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {listings.map((l) => (
                  <TableRow key={l.id} className="hover:bg-muted/30">
                    <TableCell><PlatformBadge platform={l.platform} /></TableCell>
                    <TableCell className="max-w-xs truncate text-sm">{l.title_en || '-'}</TableCell>
                    <TableCell className="font-medium">{formatPrice(l.price_usd, 'USD')}</TableCell>
                    <TableCell><StatusBadge status={l.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* SNS投稿 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Share2 className="h-4 w-4 text-muted-foreground" />
            SNS投稿
          </CardTitle>
          <Button
            variant="outline" size="sm" onClick={handleSnsGenerate} disabled={snsGenLoading}
          >
            <Sparkles className="mr-1 h-3 w-3" />
            {snsGenLoading ? 'AI生成中...' : 'AI生成'}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Platform</Label>
            <Select value={snsPlatform} onValueChange={(v) => setSnsPlatform(v as SnsPlatform)}>
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
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Body</Label>
            <Textarea
              value={snsBody} onChange={(e) => setSnsBody(e.target.value)}
              rows={4} maxLength={snsCharLimit}
              placeholder="投稿本文を入力..." className="resize-none"
            />
            <div className="flex items-center justify-between mt-1">
              <div className="flex-1 mr-4">
                <div className="h-1 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      snsCharRatio > 0.9 ? 'bg-red-500' : snsCharRatio > 0.7 ? 'bg-amber-500' : 'bg-foreground/20'
                    }`}
                    style={{ width: `${Math.min(snsCharRatio * 100, 100)}%` }}
                  />
                </div>
              </div>
              <span className={`text-xs tabular-nums ${snsCharRatio > 0.9 ? 'text-red-500' : 'text-muted-foreground'}`}>
                {snsBody.length}/{snsCharLimit}
              </span>
            </div>
          </div>
          <div>
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Hashtags</Label>
            <Input value={snsHashtags} onChange={(e) => setSnsHashtags(e.target.value)} placeholder="#japanese #tenugui" className="h-10" />
          </div>
          <Button onClick={handleSnsPost} disabled={snsPosting}>
            <Send className="mr-1.5 h-3.5 w-3.5" />
            {snsPosting ? '投稿中...' : '投稿する'}
          </Button>
        </CardContent>
      </Card>

      {/* スティッキー保存バー */}
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-7xl flex items-center justify-between px-4 py-3 md:px-6 lg:px-8">
          <div className="text-sm text-muted-foreground">
            {isDirty ? (
              <span className="text-amber-600 font-medium">未保存の変更があります</span>
            ) : (
              <span>変更なし</span>
            )}
          </div>
          <Button onClick={handleSave} disabled={saving || !isDirty}>
            <Save className="mr-1.5 h-4 w-4" />
            {saving ? '保存中...' : '変更を保存'}
          </Button>
        </div>
      </div>
    </div>
  )
}

/** ワークフローステップバッジ */
function StepBadge({ label, done, error, loading }: { label: string; done: boolean; error?: boolean; loading?: boolean }) {
  if (loading) {
    return (
      <Badge variant="outline" className="text-xs px-2 py-0.5 gap-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        {label}
      </Badge>
    )
  }
  if (error) {
    return (
      <Badge variant="outline" className="text-xs px-2 py-0.5 gap-1 border-red-300 text-red-700 dark:border-red-700 dark:text-red-400">
        <AlertTriangle className="h-3 w-3" />
        {label}
      </Badge>
    )
  }
  if (done) {
    return (
      <Badge variant="outline" className="text-xs px-2 py-0.5 gap-1 border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-400">
        <CheckCircle className="h-3 w-3" />
        {label}
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="text-xs px-2 py-0.5 text-muted-foreground">
      {label}
    </Badge>
  )
}
