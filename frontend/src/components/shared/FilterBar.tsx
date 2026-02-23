import { Search, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export interface FilterOption {
  id: string
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}

interface FilterBarProps {
  filters: FilterOption[]
  searchValue?: string
  onSearchChange?: (value: string) => void
  searchPlaceholder?: string
  activeFilters?: { label: string; onRemove: () => void }[]
  trailing?: React.ReactNode
}

export function FilterBar({
  filters,
  searchValue,
  onSearchChange,
  searchPlaceholder = '検索...',
  activeFilters,
  trailing,
}: FilterBarProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {filters.map((filter) => (
          <Select
            key={filter.id}
            value={filter.value}
            onValueChange={filter.onChange}
          >
            <SelectTrigger className="w-[160px] h-9" aria-label={filter.label}>
              <SelectValue placeholder={filter.label} />
            </SelectTrigger>
            <SelectContent>
              {filter.options.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ))}

        {onSearchChange && (
          <div className="relative ml-auto">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder={searchPlaceholder}
              value={searchValue || ''}
              onChange={(e) => onSearchChange(e.target.value)}
              className="h-9 w-[220px] pl-8"
              aria-label="検索"
            />
          </div>
        )}

        {trailing}
      </div>

      {/* アクティブフィルター表示 */}
      {activeFilters && activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted-foreground">絞り込み:</span>
          {activeFilters.map((f, i) => (
            <Badge
              key={i}
              variant="secondary"
              className="gap-1 pl-2 pr-1 py-0.5 text-xs cursor-pointer hover:bg-secondary/80"
              onClick={f.onRemove}
            >
              {f.label}
              <X className="h-3 w-3" />
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
