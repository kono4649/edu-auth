import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { Navbar } from './components/Navbar'
import { PrivateRoute } from './components/PrivateRoute'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Products } from './pages/Products'
import { Orders } from './pages/Orders'
import { Admin } from './pages/Admin'
import { Forbidden } from './pages/Forbidden'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
          <Navbar />
          <Routes>
            {/* パブリックルート（認証不要） */}
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/products" element={<Products />} />
            <Route path="/forbidden" element={<Forbidden />} />

            {/* 保護ルート（認証必要） */}
            <Route
              path="/orders"
              element={
                <PrivateRoute>
                  <Orders />
                </PrivateRoute>
              }
            />

            {/* 管理者専用ルート（認証 + admin ロール必要） */}
            <Route
              path="/admin"
              element={
                <PrivateRoute requireAdmin>
                  <Admin />
                </PrivateRoute>
              }
            />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
