import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Navbar() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <nav style={styles.nav}>
      <div style={styles.brand}>
        <Link to="/" style={styles.brandLink}>
          🛍️ Auth-NZ Shop
        </Link>
      </div>
      <div style={styles.links}>
        <Link to="/products" style={styles.link}>
          商品一覧
        </Link>
        {isAuthenticated && (
          <Link to="/orders" style={styles.link}>
            注文履歴
          </Link>
        )}
        {isAdmin && (
          <Link to="/admin" style={{ ...styles.link, ...styles.adminLink }}>
            管理画面
          </Link>
        )}
      </div>
      <div style={styles.auth}>
        {isAuthenticated ? (
          <>
            <span style={styles.userInfo}>
              {user?.username}
              <span style={user?.role === 'admin' ? styles.adminBadge : styles.userBadge}>
                {user?.role === 'admin' ? 'ADMIN' : 'USER'}
              </span>
            </span>
            <button onClick={handleLogout} style={styles.button}>
              ログアウト
            </button>
          </>
        ) : (
          <>
            <Link to="/login" style={styles.link}>
              ログイン
            </Link>
            <Link to="/register" style={{ ...styles.link, ...styles.registerLink }}>
              新規登録
            </Link>
          </>
        )}
      </div>
    </nav>
  )
}

const styles: Record<string, React.CSSProperties> = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.75rem 2rem',
    backgroundColor: '#1a1a2e',
    color: 'white',
    boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
  },
  brand: { fontWeight: 'bold', fontSize: '1.2rem' },
  brandLink: { color: 'white', textDecoration: 'none' },
  links: { display: 'flex', gap: '1.5rem' },
  link: { color: '#ccc', textDecoration: 'none', fontSize: '0.95rem' },
  adminLink: { color: '#ffd700' },
  auth: { display: 'flex', alignItems: 'center', gap: '1rem' },
  userInfo: { fontSize: '0.9rem', color: '#ccc', display: 'flex', alignItems: 'center', gap: '0.5rem' },
  adminBadge: {
    background: '#ffd700',
    color: '#1a1a2e',
    padding: '0.1rem 0.4rem',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 'bold',
  },
  userBadge: {
    background: '#4caf50',
    color: 'white',
    padding: '0.1rem 0.4rem',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 'bold',
  },
  button: {
    background: 'transparent',
    border: '1px solid #ccc',
    color: '#ccc',
    padding: '0.3rem 0.8rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem',
  },
  registerLink: { color: '#4fc3f7' },
}
