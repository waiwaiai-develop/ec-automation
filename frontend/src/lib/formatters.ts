export function formatPrice(value: number | null | undefined, currency: 'JPY' | 'USD' = 'JPY'): string {
  if (value == null) return '-'
  if (currency === 'USD') {
    return `$${value.toFixed(2)}`
  }
  return `¥${Math.round(value).toLocaleString()}`
}

export function parseImages(raw: string | null | undefined): string[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed
  } catch {
    // パース失敗
  }
  return []
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

export function formatMargin(margin: number | null | undefined): string {
  if (margin == null) return '-'
  return `${(margin * 100).toFixed(1)}%`
}
