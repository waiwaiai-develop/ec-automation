import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { AppLayout } from '@/components/layout/AppLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProductsPage } from '@/pages/ProductsPage'
import { ProductDetailPage } from '@/pages/ProductDetailPage'
import { ListingsPage } from '@/pages/ListingsPage'
import { OrdersPage } from '@/pages/OrdersPage'
import { SnsPage } from '@/pages/SnsPage'
import { ResearchPage } from '@/pages/ResearchPage'
import { ResearchDetailPage } from '@/pages/ResearchDetailPage'

export default function App() {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <BrowserRouter basename="/app">
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="products" element={<ProductsPage />} />
              <Route path="products/:id" element={<ProductDetailPage />} />
              <Route path="listings" element={<ListingsPage />} />
              <Route path="orders" element={<OrdersPage />} />
              <Route path="research" element={<ResearchPage />} />
              <Route path="research/:id" element={<ResearchDetailPage />} />
              <Route path="sns" element={<SnsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster />
      </TooltipProvider>
    </ThemeProvider>
  )
}
