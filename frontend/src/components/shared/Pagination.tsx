import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface PaginationProps {
  offset: number
  limit: number
  total: number
  onPageChange: (newOffset: number) => void
}

export function Pagination({ offset, limit, total, onPageChange }: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1
  const totalPages = Math.max(1, Math.ceil(total / limit))
  const hasPrev = offset > 0
  const hasNext = offset + limit < total

  return (
    <div className="flex items-center justify-between px-2 py-3">
      <p className="text-xs text-muted-foreground tabular-nums">
        {total > 0
          ? `${offset + 1}–${Math.min(offset + limit, total)} / ${total}件`
          : '0件'}
      </p>
      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          className="h-7 px-2"
          disabled={!hasPrev}
          onClick={() => onPageChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft className="h-3.5 w-3.5 mr-0.5" />
          前へ
        </Button>
        <span className="text-xs text-muted-foreground tabular-nums px-2">
          {currentPage} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          className="h-7 px-2"
          disabled={!hasNext}
          onClick={() => onPageChange(offset + limit)}
        >
          次へ
          <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
        </Button>
      </div>
    </div>
  )
}
