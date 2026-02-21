import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { SnsPost } from '@/types'

const DAY_LABELS = ['日', '月', '火', '水', '木', '金', '土'] as const

// プラットフォーム別ドット色
const PLATFORM_DOT_COLOR: Record<string, string> = {
  twitter: 'bg-sky-500',
  instagram: 'bg-pink-500',
  threads: 'bg-neutral-700 dark:bg-neutral-300',
}

interface MonthCalendarProps {
  year: number
  month: number // 0-indexed
  posts: SnsPost[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
  onMonthChange: (year: number, month: number) => void
}

/** YYYY-MM-DD 文字列を返す */
function formatDate(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

/** 今日の YYYY-MM-DD */
function todayStr(): string {
  const now = new Date()
  return formatDate(now.getFullYear(), now.getMonth(), now.getDate())
}

/** 月の日数 */
function daysInMonth(y: number, m: number): number {
  return new Date(y, m + 1, 0).getDate()
}

/** 月初の曜日 (0=日曜) */
function firstDayOfWeek(y: number, m: number): number {
  return new Date(y, m, 1).getDay()
}

/** 投稿を日付ごとにグループ化 */
function groupByDate(posts: SnsPost[]): Map<string, Set<string>> {
  const map = new Map<string, Set<string>>()
  for (const post of posts) {
    const at = post.scheduled_at || post.created_at
    if (!at) continue
    const dateKey = at.slice(0, 10) // YYYY-MM-DD
    if (!map.has(dateKey)) map.set(dateKey, new Set())
    map.get(dateKey)!.add(post.platform)
  }
  return map
}

export function MonthCalendar({
  year,
  month,
  posts,
  selectedDate,
  onDateSelect,
  onMonthChange,
}: MonthCalendarProps) {
  const today = todayStr()
  const days = daysInMonth(year, month)
  const startDay = firstDayOfWeek(year, month)
  const postsByDate = groupByDate(posts)

  // 前月・次月
  function goPrev() {
    if (month === 0) onMonthChange(year - 1, 11)
    else onMonthChange(year, month - 1)
  }
  function goNext() {
    if (month === 11) onMonthChange(year + 1, 0)
    else onMonthChange(year, month + 1)
  }

  // グリッド行を構築
  const cells: (number | null)[] = []
  for (let i = 0; i < startDay; i++) cells.push(null)
  for (let d = 1; d <= days; d++) cells.push(d)
  // 最終行を7の倍数に埋める
  while (cells.length % 7 !== 0) cells.push(null)

  return (
    <div className="select-none">
      {/* ヘッダー: 前月 / 年月 / 次月 */}
      <div className="flex items-center justify-between mb-3">
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={goPrev}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-semibold">
          {year}年{month + 1}月
        </span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={goNext}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* 曜日ラベル */}
      <div className="grid grid-cols-7 mb-1">
        {DAY_LABELS.map((label, i) => (
          <div
            key={label}
            className={`text-center text-[11px] font-medium pb-1 ${
              i === 0 ? 'text-red-400' : i === 6 ? 'text-blue-400' : 'text-muted-foreground'
            }`}
          >
            {label}
          </div>
        ))}
      </div>

      {/* 日付グリッド */}
      <div className="grid grid-cols-7 gap-px">
        {cells.map((day, idx) => {
          if (day === null) {
            return <div key={`empty-${idx}`} className="h-10" />
          }

          const dateStr = formatDate(year, month, day)
          const isToday = dateStr === today
          const isSelected = dateStr === selectedDate
          const dayOfWeek = idx % 7
          const platforms = postsByDate.get(dateStr)

          return (
            <button
              key={dateStr}
              type="button"
              onClick={() => onDateSelect(dateStr)}
              className={`relative flex flex-col items-center justify-center h-10 rounded-md text-sm transition-colors
                ${isSelected
                  ? 'bg-primary text-primary-foreground font-semibold'
                  : isToday
                    ? 'bg-accent font-semibold ring-1 ring-primary/40'
                    : 'hover:bg-muted'
                }
                ${!isSelected && dayOfWeek === 0 ? 'text-red-400' : ''}
                ${!isSelected && dayOfWeek === 6 ? 'text-blue-400' : ''}
              `}
            >
              {day}
              {/* プラットフォーム別ドット */}
              {platforms && platforms.size > 0 && (
                <span className="flex gap-0.5 absolute bottom-0.5">
                  {Array.from(platforms).slice(0, 3).map((p) => (
                    <span
                      key={p}
                      className={`block h-1 w-1 rounded-full ${
                        isSelected ? 'bg-primary-foreground/70' : (PLATFORM_DOT_COLOR[p] || 'bg-muted-foreground')
                      }`}
                    />
                  ))}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
