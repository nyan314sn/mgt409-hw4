import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar.tsx'
import Footer from './components/Footer.tsx'
import ChatWidget from './components/ChatWidget.tsx'
import Spotlight from './components/Spotlight.tsx'
import AuthProvider from './components/AuthProvider.tsx'
import ChatProvider from './components/ChatProvider.tsx'
import CartProvider from './components/CartProvider.tsx'
import OfflineBanner from './components/OfflineBanner.tsx'
import Home from './pages/Home.tsx'
import Products from './pages/Products.tsx'
import ProductDetail from './pages/ProductDetail.tsx'
import About from './pages/About.tsx'
import Login from './pages/Login.tsx'
import Register from './pages/Register.tsx'
import NotFound from './pages/NotFound.tsx'
import Cart from './pages/Cart.tsx'
import Checkout from './pages/Checkout.tsx'
import { OrderDetail, OrderList } from './pages/Orders.tsx'
import AdminUsage from './pages/AdminUsage.tsx'

export default function App() {
  const { pathname } = useLocation()
  // Braces matter: in newer Chrome scrollTo() returns a Promise, and an effect that returns
  // anything but a cleanup function crashes React.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <AuthProvider>
      <CartProvider>
        <ChatProvider>
          <a className="skip-link" href="#main">Skip to content</a>
          <OfflineBanner />
          <NavBar />
          <main id="main">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/products" element={<Products />} />
              <Route path="/products/:id" element={<ProductDetail />} />
              <Route path="/about" element={<About />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/orders" element={<OrderList />} />
            <Route path="/orders/:orderNumber" element={<OrderDetail />} />
            <Route path="/admin/usage" element={<AdminUsage />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
          <Footer />
          <Spotlight />
          <ChatWidget />
        </ChatProvider>
      </CartProvider>
    </AuthProvider>
  )
}
