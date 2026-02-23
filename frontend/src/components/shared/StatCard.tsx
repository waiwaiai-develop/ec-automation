import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  description?: string
  trend?: {
    value: number
    label?: string
  }
  iconColor?: string
}

export function StatCard({ title, value, icon: Icon, description, trend, iconColor }: StatCardProps) {
  return (
    <Card className="group hover:shadow-md transition-shadow duration-200">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${iconColor || 'bg-primary/10'}`}>
          <Icon className={`h-4 w-4 ${iconColor ? 'text-white' : 'text-primary'}`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-2 mt-1">
          {trend && (
            <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${
              trend.value >= 0 ? 'text-emerald-600' : 'text-red-600'
            }`}>
              {trend.value >= 0 ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {trend.value >= 0 ? '+' : ''}{trend.value}%
              {trend.label && <span className="text-muted-foreground font-normal ml-0.5">{trend.label}</span>}
            </span>
          )}
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
