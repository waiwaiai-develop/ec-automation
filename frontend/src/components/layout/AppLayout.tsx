import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

const pageTitles: Record<string, string> = {
  '/': 'ダッシュボード',
  '/products': '商品管理',
  '/listings': '出品管理',
  '/orders': '注文管理',
  '/sns': 'SNS投稿',
  '/research': '需要分析',
}

// パンくず生成ルール
function buildBreadcrumbs(pathname: string): Array<{ label: string; to?: string }> {
  const crumbs: Array<{ label: string; to?: string }> = []

  // 商品詳細
  if (pathname.match(/^\/products\/\d+/)) {
    crumbs.push({ label: 'ダッシュボード', to: '/' })
    crumbs.push({ label: '商品管理', to: '/products' })
    crumbs.push({ label: '商品詳細' })
    return crumbs
  }

  // リサーチ詳細
  if (pathname.match(/^\/research\/\d+/)) {
    crumbs.push({ label: 'ダッシュボード', to: '/' })
    crumbs.push({ label: '需要分析', to: '/research' })
    crumbs.push({ label: '分析結果' })
    return crumbs
  }

  // 通常のトップレベルページ
  const title = pageTitles[pathname]
  if (title && pathname !== '/') {
    crumbs.push({ label: 'ダッシュボード', to: '/' })
    crumbs.push({ label: title })
  }

  return crumbs
}

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const isProductDetail = location.pathname.match(/^\/products\/\d+/)
  const isResearchDetail = location.pathname.match(/^\/research\/\d+/)
  const title = isProductDetail
    ? '商品詳細'
    : isResearchDetail
      ? '分析結果'
      : pageTitles[location.pathname] || 'EC Automation'

  const breadcrumbs = buildBreadcrumbs(location.pathname)

  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title={title}
          breadcrumbs={breadcrumbs}
          onMenuClick={() => setSidebarOpen(true)}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
