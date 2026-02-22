// --- 商品 ---
export interface Product {
  id: number
  supplier: string
  supplier_product_id: string
  name_ja: string
  name_en: string | null
  description_ja: string | null
  description_en: string | null
  category: string | null
  wholesale_price_jpy: number | null
  reference_price_jpy: number | null
  weight_g: number | null
  image_urls: string | null
  stock_status: string | null
  product_url: string | null
  supplier_id: string | null
  shop_name: string | null
  spec_text: string | null
  netsea_category_id: number | null
  direct_send_flag: string | null
  image_copy_flag: string | null
  deal_net_shop_flag: string | null
  deal_net_auction_flag: string | null
  list_on_ebay: number
  list_on_base: number
  list_on_shopify: number
  created_at: string
  updated_at: string
}

// --- リスティング ---
export interface Listing {
  id: number
  product_id: number
  platform: string
  platform_listing_id: string | null
  title_en: string | null
  description_en: string | null
  tags: string | null
  price_usd: number | null
  shipping_cost_usd: number | null
  status: string
  ban_check_passed: number | null
  ban_check_issues: string | null
  excluded_countries: string | null
  views: number | null
  favorites: number | null
  sales: number | null
  created_at: string
  updated_at: string
}

// --- 注文 ---
export interface Order {
  id: number
  listing_id: number | null
  product_id: number | null
  platform: string
  platform_order_id: string | null
  buyer_name: string | null
  buyer_country: string | null
  sale_price_usd: number | null
  shipping_cost_usd: number | null
  platform_fees_usd: number | null
  profit_usd: number | null
  status: string
  supplier_order_id: string | null
  tracking_number: string | null
  ordered_at: string | null
  shipped_at: string | null
  delivered_at: string | null
}

// --- 統計 ---
export interface Stats {
  products: number
  listings: number
  orders: number
  brand_blacklist: number
  country_restrictions: number
  ebay_market_data: number
  sync_log: number
  products_by_supplier: Record<string, number>
  products_by_category: Record<string, number>
}

export interface DailySummary {
  date: string
  orders_count: number
  revenue_usd: number
  profit_usd: number
  active_listings: number
  stock_changes: number
}

// --- 利益計算 ---
export interface ProfitCalc {
  sale_usd: number
  wholesale_usd: number
  shipping_usd: number
  platform_fees_usd: number
  profit_usd: number
  profit_margin: number
  profitable: boolean
}

// --- APIレスポンス ---
export interface DashboardResponse {
  stats: Stats
  daily_summary: DailySummary
}

export interface ProductsResponse {
  products: Product[]
  categories: string[]
  total: number
  limit: number
  offset: number
}

export interface ProductDetailResponse {
  product: Product
  images: string[]
  profit_info: ProfitCalc[] | null
  listings: Listing[]
}

export interface ListingsResponse {
  listings: Listing[]
  total: number
  limit: number
  offset: number
}

export interface OrdersResponse {
  orders: Order[]
  total: number
  limit: number
  offset: number
}

export interface ApiError {
  error: string
}

export interface ApiSuccess {
  success: boolean
  message: string
}

// --- SNS投稿 ---
export type SnsPlatform = 'twitter' | 'instagram' | 'threads'
export type SnsPostStatus = 'draft' | 'scheduled' | 'posted' | 'failed'

export interface SnsPost {
  id: number
  product_id: number | null
  platform: SnsPlatform
  body: string
  image_urls: string | null
  hashtags: string | null
  status: SnsPostStatus
  scheduled_at: string | null
  posted_at: string | null
  platform_post_id: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface SnsPostsResponse {
  posts: SnsPost[]
  total: number
  limit: number
  offset: number
}

// --- ダッシュボード拡張 ---
export interface DailyHistory {
  date: string
  orders_count: number
  revenue_usd: number
  profit_usd: number
}

export interface HistoryResponse {
  history: DailyHistory[]
  days: number
}

export interface PlatformStatEntry {
  listings_total: number
  listings_active: number
  orders: number
  revenue_usd: number
  profit_usd: number
}

export interface PlatformStatsResponse {
  platforms: Record<string, PlatformStatEntry>
}

export interface ScoringCandidate {
  id: number
  name_ja: string
  name_en: string | null
  category: string | null
  wholesale_price_jpy: number | null
  stock_status: string | null
  score: number
  max_score: number
  reasons: string[]
}

export interface ScoringResponse {
  candidates: ScoringCandidate[]
}
