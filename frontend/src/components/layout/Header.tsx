import { Link } from 'react-router-dom'
import { Menu, Moon, Sun, Bell, ChevronRight, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from './ThemeProvider'

interface Breadcrumb {
  label: string
  to?: string
}

interface HeaderProps {
  title: string
  breadcrumbs?: Breadcrumb[]
  onMenuClick: () => void
}

export function Header({ title, breadcrumbs, onMenuClick }: HeaderProps) {
  const { theme, toggle } = useTheme()

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-border bg-background/80 px-6 backdrop-blur-md">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
        aria-label="メニューを開く"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="flex flex-col justify-center min-w-0">
        {/* パンくずリスト */}
        {breadcrumbs && breadcrumbs.length > 0 ? (
          <nav className="flex items-center gap-1 text-xs text-muted-foreground" aria-label="パンくずリスト">
            {breadcrumbs.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1">
                {i > 0 && <ChevronRight className="h-3 w-3" />}
                {crumb.to ? (
                  <Link to={crumb.to} className="hover:text-foreground transition-colors">
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-foreground font-medium">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        ) : (
          <h1 className="text-sm font-semibold tracking-tight truncate">{title}</h1>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1">
        {/* Cmd+K ヒント */}
        <div className="hidden md:flex items-center gap-1 rounded-md border border-border/60 bg-muted/50 px-2 py-1 mr-2">
          <kbd className="text-[10px] font-mono text-muted-foreground">⌘K</kbd>
        </div>

        {/* 通知ベル */}
        <Button
          variant="ghost"
          size="icon"
          className="rounded-lg hover:bg-muted relative"
          aria-label="通知"
        >
          <Bell className="h-4 w-4" />
        </Button>

        {/* テーマ切替 */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          className="rounded-lg hover:bg-muted"
          aria-label={theme === 'dark' ? 'ライトモードに切替' : 'ダークモードに切替'}
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>

        {/* ユーザーアバター */}
        <Button
          variant="ghost"
          size="icon"
          className="rounded-lg hover:bg-muted"
          aria-label="ユーザー設定"
        >
          <User className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
