import { Badge } from '@/components/ui/badge'
import type { SnsPlatform, SnsPostStatus } from '@/types'

// --- SNS Platform SVG Icons ---
function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
    </svg>
  )
}

function ThreadsIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.187.408-2.26 1.33-3.016.88-.722 2.082-1.127 3.384-1.138l.163-.002c.853 0 1.63.117 2.322.351.008-.655-.05-1.27-.174-1.838l2.03-.425c.16.739.246 1.537.258 2.386 1.168.834 2.01 1.92 2.458 3.2.79 2.258.255 4.917-1.43 6.617-1.857 1.87-4.164 2.681-7.264 2.547zm-.273-7.607c-1.696.072-2.712.86-2.672 2.07.018.43.222.885.572 1.112.508.33 1.275.478 2.158.434 1.073-.06 1.895-.44 2.443-1.122.433-.537.744-1.276.908-2.189-.62-.207-1.315-.317-2.073-.317l-.163.002-.338.009-.835.001z" />
    </svg>
  )
}

export { XIcon, InstagramIcon, ThreadsIcon }

// --- 既存バッジ ---

export function StockBadge({ status }: { status: string | null }) {
  if (!status) return <Badge variant="outline" className="text-muted-foreground">不明</Badge>
  const map: Record<string, { label: string; className: string }> = {
    in_stock: { label: '在庫あり', className: 'bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:text-emerald-400 dark:border-emerald-800' },
    out_of_stock: { label: '在庫切れ', className: 'bg-red-500/10 text-red-700 border-red-200 dark:text-red-400 dark:border-red-800' },
    limited: { label: '残りわずか', className: 'bg-amber-500/10 text-amber-700 border-amber-200 dark:text-amber-400 dark:border-amber-800' },
  }
  const m = map[status] || { label: status, className: '' }
  return <Badge variant="outline" className={m.className}>{m.label}</Badge>
}

export function PlatformBadge({ platform }: { platform: string }) {
  const config: Record<string, { label: string; className: string }> = {
    ebay: { label: 'eBay', className: 'bg-blue-600 text-white' },
    base: { label: 'BASE', className: 'bg-orange-500 text-white' },
    shopify: { label: 'Shopify', className: 'bg-emerald-600 text-white' },
  }
  const c = config[platform] || { label: platform.toUpperCase(), className: 'bg-gray-500 text-white' }
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${c.className}`}>
      {c.label}
    </span>
  )
}

export function DSFlagBadge({ direct, image, shop }: { direct: string | null; image: string | null; shop: string | null }) {
  const allOk = direct === 'Y' && image === 'Y' && shop === 'Y'
  if (allOk) {
    return (
      <Badge variant="outline" className="bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:text-emerald-400 dark:border-emerald-800">
        DS OK
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="text-muted-foreground border-dashed">
      DS --
    </Badge>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { className: string }> = {
    active: { className: 'bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:text-emerald-400' },
    draft: { className: 'bg-slate-500/10 text-slate-600 border-slate-200 dark:text-slate-400' },
    ended: { className: 'bg-gray-500/10 text-gray-500 border-gray-200' },
    paused: { className: 'bg-amber-500/10 text-amber-700 border-amber-200 dark:text-amber-400' },
    pending: { className: 'bg-blue-500/10 text-blue-700 border-blue-200 dark:text-blue-400' },
    purchased: { className: 'bg-indigo-500/10 text-indigo-700 border-indigo-200 dark:text-indigo-400' },
    shipped: { className: 'bg-cyan-500/10 text-cyan-700 border-cyan-200 dark:text-cyan-400' },
    delivered: { className: 'bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:text-emerald-400' },
    issue: { className: 'bg-red-500/10 text-red-700 border-red-200 dark:text-red-400' },
    cancelled: { className: 'bg-red-500/10 text-red-700 border-red-200 dark:text-red-400' },
  }
  const m = map[status] || { className: '' }
  return <Badge variant="outline" className={m.className}>{status}</Badge>
}

// --- SNSバッジ ---

export function SnsPlatformBadge({ platform }: { platform: SnsPlatform }) {
  const config: Record<SnsPlatform, { label: string; icon: React.ReactNode; className: string }> = {
    twitter: {
      label: 'X',
      icon: <XIcon className="h-3 w-3" />,
      className: 'bg-black text-white dark:bg-white dark:text-black',
    },
    instagram: {
      label: 'Instagram',
      icon: <InstagramIcon className="h-3 w-3" />,
      className: 'bg-pink-600 text-white',
    },
    threads: {
      label: 'Threads',
      icon: <ThreadsIcon className="h-3 w-3" />,
      className: 'bg-black text-white dark:bg-white dark:text-black',
    },
  }
  const c = config[platform] || { label: platform, icon: null, className: 'bg-gray-500 text-white' }
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${c.className}`}>
      {c.icon}
      {c.label}
    </span>
  )
}

export function SnsStatusBadge({ status }: { status: SnsPostStatus }) {
  const map: Record<SnsPostStatus, { label: string; className: string }> = {
    draft: { label: '下書き', className: 'bg-slate-500/10 text-slate-600 border-slate-200 dark:text-slate-400' },
    scheduled: { label: '予約済み', className: 'bg-blue-500/10 text-blue-700 border-blue-200 dark:text-blue-400' },
    posted: { label: '投稿済み', className: 'bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:text-emerald-400' },
    failed: { label: '失敗', className: 'bg-red-500/10 text-red-700 border-red-200 dark:text-red-400' },
  }
  const m = map[status] || { label: status, className: '' }
  return <Badge variant="outline" className={m.className}>{m.label}</Badge>
}
