import { NavLink } from 'react-router-dom'
import { Home, Package, ShoppingCart, Search, Share2, X, ClipboardList, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface NavSection {
  label: string
  items: { to: string; icon: typeof Home; label: string }[]
}

const navSections: NavSection[] = [
  {
    label: '分析',
    items: [
      { to: '/', icon: Home, label: 'ダッシュボード' },
      { to: '/research', icon: Search, label: '需要分析' },
    ],
  },
  {
    label: '運営',
    items: [
      { to: '/products', icon: Package, label: '商品管理' },
      { to: '/listings', icon: ShoppingCart, label: '出品管理' },
      { to: '/orders', icon: ClipboardList, label: '注文管理' },
    ],
  },
  {
    label: 'マーケティング',
    items: [
      { to: '/sns', icon: Share2, label: 'SNS投稿' },
    ],
  },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed top-0 left-0 z-50 flex h-full w-60 flex-col bg-sidebar text-sidebar-foreground transition-transform duration-300 ease-in-out lg:static lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* ロゴ */}
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground text-xs font-bold">
              EC
            </div>
            <div>
              <span className="text-sm font-bold tracking-tight text-sidebar-foreground">EC Automation</span>
              <p className="text-[10px] text-sidebar-foreground/50 leading-none">Japan Dropship</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden text-sidebar-foreground hover:bg-sidebar-accent"
            onClick={onClose}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="mx-4 h-px bg-sidebar-border" />

        {/* ナビゲーション */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navSections.map((section) => (
            <div key={section.label}>
              <p className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={to === '/'}
                    onClick={onClose}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-sidebar-accent text-sidebar-primary-foreground border-l-2 border-sidebar-primary'
                          : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
                      )
                    }
                  >
                    <Icon className="h-4 w-4" />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* フッター: ユーザー設定エリア */}
        <div className="border-t border-sidebar-border px-3 py-3">
          <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors cursor-pointer">
            <Settings className="h-4 w-4" />
            <span className="text-sm">設定</span>
            <span className="ml-auto text-[10px] text-sidebar-foreground/30">v0.3.0</span>
          </div>
        </div>
      </aside>
    </>
  )
}
