import { useState } from 'react'
import { Outlet, useLocation, Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

const pageTitles: Record<string, string> = {
  '/': 'ダッシュボード',
  '/products': '商品管理',
  '/listings': '出品管理',
  '/orders': '注文管理',
  '/sns': 'SNS投稿',
}

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const isProductDetail = location.pathname.match(/^\/products\/\d+/)
  const title = isProductDetail
    ? '商品詳細'
    : pageTitles[location.pathname] || 'EC Automation'

  // パンくずリスト構築
  const breadcrumbs: Array<{ label: string; to?: string }> = []
  if (isProductDetail) {
    breadcrumbs.push({ label: 'ダッシュボード', to: '/' })
    breadcrumbs.push({ label: '商品管理', to: '/products' })
    breadcrumbs.push({ label: '商品詳細' })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            {breadcrumbs.length > 0 && (
              <nav className="flex items-center gap-1 text-xs text-muted-foreground mb-4">
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
            )}
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
