import type {
  DashboardResponse,
  ProductsResponse,
  ProductDetailResponse,
  ListingsResponse,
  OrdersResponse,
  SnsPostsResponse,
  SnsPost,
  SnsPlatform,
  SnsPostStatus,
  HistoryResponse,
  PlatformStatsResponse,
  ScoringResponse,
} from '@/types'

const BASE = '/api'

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.error || `API error: ${res.status}`)
  }
  return data as T
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return fetchJson<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// --- GET API ---

export function getDashboard() {
  return fetchJson<DashboardResponse>(`${BASE}/dashboard`)
}

export function getDashboardHistory(days: number = 30) {
  return fetchJson<HistoryResponse>(`${BASE}/dashboard/history?days=${days}`)
}

export function getPlatformStats() {
  return fetchJson<PlatformStatsResponse>(`${BASE}/dashboard/platform-stats`)
}

export function getProductsScoring() {
  return fetchJson<ScoringResponse>(`${BASE}/products/scoring`)
}

export function getProducts(params?: {
  category?: string
  stock_status?: string
  ds_only?: string
  limit?: number
  offset?: number
  search?: string
}) {
  const sp = new URLSearchParams()
  if (params?.category) sp.set('category', params.category)
  if (params?.stock_status) sp.set('stock_status', params.stock_status)
  if (params?.ds_only) sp.set('ds_only', params.ds_only)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  if (params?.search) sp.set('search', params.search)
  const qs = sp.toString()
  return fetchJson<ProductsResponse>(`${BASE}/products${qs ? '?' + qs : ''}`)
}

export function getProductDetail(id: number) {
  return fetchJson<ProductDetailResponse>(`${BASE}/products/${id}`)
}

export function getListings(params?: {
  platform?: string
  status?: string
  limit?: number
  offset?: number
  search?: string
}) {
  const sp = new URLSearchParams()
  if (params?.platform) sp.set('platform', params.platform)
  if (params?.status) sp.set('status', params.status)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  if (params?.search) sp.set('search', params.search)
  const qs = sp.toString()
  return fetchJson<ListingsResponse>(`${BASE}/listings${qs ? '?' + qs : ''}`)
}

export function getOrders(params?: {
  platform?: string
  status?: string
  limit?: number
  offset?: number
  search?: string
}) {
  const sp = new URLSearchParams()
  if (params?.platform) sp.set('platform', params.platform)
  if (params?.status) sp.set('status', params.status)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  if (params?.search) sp.set('search', params.search)
  const qs = sp.toString()
  return fetchJson<OrdersResponse>(`${BASE}/orders${qs ? '?' + qs : ''}`)
}

// --- POST API ---

export function importNetseaUrl(url: string) {
  return postJson<{ success: boolean; product_id: number; name_ja: string; message: string }>(
    `${BASE}/products/import-netsea-url`,
    { url }
  )
}

export function bulkDelete(productIds: number[]) {
  return postJson<{ success: boolean; deleted: number; message: string }>(
    `${BASE}/products/bulk-delete`,
    { product_ids: productIds }
  )
}

export function bulkSetFlags(productIds: number[], flags: Record<string, number>) {
  return postJson<{ success: boolean; updated: number; message: string }>(
    `${BASE}/products/bulk-set-flags`,
    { product_ids: productIds, flags }
  )
}

export function updateProduct(id: number, data: Record<string, unknown>) {
  return postJson<{ success: boolean; message: string }>(
    `${BASE}/products/${id}/update`,
    data
  )
}

export function generateListing(id: number) {
  return postJson<{
    success: boolean
    title: string
    description: string
    tags: string[]
    item_specifics: Record<string, string>
  }>(`${BASE}/products/${id}/generate`, {})
}

export function generateListingJa(id: number) {
  return postJson<{
    success: boolean
    title_ja: string
    description_ja: string
  }>(`${BASE}/products/${id}/generate-ja`, {})
}

export function banCheck(id: number) {
  return postJson<{
    success: boolean
    passed: boolean
    issues: string[]
    excluded_countries: string[]
  }>(`${BASE}/products/${id}/ban-check`, {})
}

export function listOnEbay(id: number, data: {
  title_en: string
  description_en: string
  price_usd: number
  tags?: string[]
}) {
  return postJson<{
    success: boolean
    listing_id: number
    platform_listing_id: string
    url: string
    message: string
  }>(`${BASE}/products/${id}/list-ebay`, data)
}

export function listOnBase(id: number, data: {
  price_jpy: number
  stock?: number
  title_ja?: string
  description_ja?: string
}) {
  return postJson<{
    success: boolean
    listing_id: number
    platform_listing_id: string
    url: string
    message: string
  }>(`${BASE}/products/${id}/list-base`, data)
}

export function bulkList(data: {
  product_ids: number[]
  platform: string
  auto_generate?: boolean
  price_usd?: number
}) {
  return postJson<{
    success: boolean
    results: Array<{ product_id: number; success: boolean; error?: string }>
    message: string
  }>(`${BASE}/products/bulk-list`, data)
}

// --- SNS API ---

export function getSnsPosts(params?: {
  platform?: SnsPlatform
  status?: SnsPostStatus
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}) {
  const sp = new URLSearchParams()
  if (params?.platform) sp.set('platform', params.platform)
  if (params?.status) sp.set('status', params.status)
  if (params?.date_from) sp.set('date_from', params.date_from)
  if (params?.date_to) sp.set('date_to', params.date_to)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  const qs = sp.toString()
  return fetchJson<SnsPostsResponse>(`${BASE}/sns/posts${qs ? '?' + qs : ''}`)
}

export function createSnsPost(data: {
  product_id?: number | null
  platform: SnsPlatform
  body: string
  hashtags?: string
  scheduled_at?: string | null
  status?: SnsPostStatus
}) {
  return postJson<{ success: boolean; post: SnsPost; message: string }>(
    `${BASE}/sns/posts`,
    data
  )
}

export function generateSnsBody(data: {
  product_id: number
  platform: SnsPlatform
}) {
  return postJson<{ success: boolean; body: string; hashtags: string }>(
    `${BASE}/sns/generate`,
    data
  )
}

export function publishSnsPost(id: number) {
  return postJson<{ success: boolean; message: string }>(
    `${BASE}/sns/posts/${id}/publish`,
    {}
  )
}

export function deleteSnsPost(id: number) {
  return postJson<{ success: boolean; message: string }>(
    `${BASE}/sns/posts/${id}/delete`,
    {}
  )
}

export function calculateProfit(id: number, saleUsd: number, platform?: string) {
  return postJson<{
    success: boolean
    sale_usd: number
    wholesale_usd: number
    shipping_usd: number
    platform_fees_usd: number
    profit_usd: number
    profit_margin: number
    profitable: boolean
  }>(`${BASE}/products/${id}/profit`, {
    sale_usd: saleUsd,
    platform: platform || 'ebay',
  })
}
