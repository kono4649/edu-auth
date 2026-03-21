import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Home() {
  const { isAuthenticated, isAdmin, user } = useAuth()

  return (
    <div style={styles.container}>
      <div style={styles.hero}>
        <h1 style={styles.title}>Auth-NZ 学習 ECサイト</h1>
        <p style={styles.subtitle}>Authentication（認証）と Authorization（認可）を実践で学ぶ</p>
        {isAuthenticated ? (
          <p style={styles.welcome}>ようこそ、{user?.username} さん！ ({user?.role})</p>
        ) : (
          <div style={styles.ctaButtons}>
            <Link to="/login" style={styles.primaryBtn}>ログイン</Link>
            <Link to="/register" style={styles.secondaryBtn}>新規登録</Link>
          </div>
        )}
      </div>

      <div style={styles.conceptGrid}>
        <div style={styles.conceptCard}>
          <h3 style={styles.conceptTitle}>🔐 Authentication（認証）</h3>
          <p style={styles.conceptDesc}>「あなたは誰ですか？」の確認</p>
          <ul style={styles.list}>
            <li>JWT によるトークンベース認証</li>
            <li>bcrypt パスワードハッシュ化</li>
            <li>アクセストークン（30分）</li>
            <li>リフレッシュトークン（7日）</li>
          </ul>
        </div>

        <div style={styles.conceptCard}>
          <h3 style={styles.conceptTitle}>🛡️ Authorization（認可）</h3>
          <p style={styles.conceptDesc}>「何が許可されていますか？」の確認</p>
          <ul style={styles.list}>
            <li>RBAC（ロールベースアクセス制御）</li>
            <li>user ロール: 閲覧・注文</li>
            <li>admin ロール: 商品管理・ユーザー管理</li>
            <li>リソースレベルの認可（自分の注文のみ）</li>
          </ul>
        </div>
      </div>

      <div style={styles.accessMatrix}>
        <h2 style={styles.matrixTitle}>アクセス権限マトリクス</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>エンドポイント</th>
              <th style={styles.th}>未認証</th>
              <th style={styles.th}>user ロール</th>
              <th style={styles.th}>admin ロール</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['GET /products', '✅', '✅', '✅'],
              ['POST /products', '❌', '❌ (403)', '✅'],
              ['DELETE /products', '❌', '❌ (403)', '✅'],
              ['GET /orders (自分の)', '❌ (401)', '✅', '✅'],
              ['GET /orders (全員の)', '❌ (401)', '❌', '✅'],
              ['POST /orders', '❌ (401)', '✅', '✅'],
              ['PUT /orders/status', '❌ (401)', '❌ (403)', '✅'],
              ['GET /admin/users', '❌ (401)', '❌ (403)', '✅'],
            ].map(([ep, guest, user, admin]) => (
              <tr key={ep}>
                <td style={styles.td}><code>{ep}</code></td>
                <td style={{ ...styles.td, ...styles.center }}>{guest}</td>
                <td style={{ ...styles.td, ...styles.center }}>{user}</td>
                <td style={{ ...styles.td, ...styles.center }}>{admin}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={styles.trySection}>
        <h2 style={styles.matrixTitle}>試してみよう</h2>
        <div style={styles.tryGrid}>
          <Link to="/products" style={styles.tryCard}>
            <span style={styles.tryIcon}>🛍️</span>
            <span>商品一覧（認証不要）</span>
          </Link>
          {isAuthenticated && (
            <Link to="/orders" style={styles.tryCard}>
              <span style={styles.tryIcon}>📦</span>
              <span>注文履歴（要認証）</span>
            </Link>
          )}
          {isAdmin && (
            <Link to="/admin" style={{ ...styles.tryCard, ...styles.adminCard }}>
              <span style={styles.tryIcon}>⚙️</span>
              <span>管理者パネル（要admin）</span>
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '2rem', maxWidth: '1000px', margin: '0 auto' },
  hero: { textAlign: 'center', padding: '3rem 0', borderBottom: '1px solid #eee', marginBottom: '2rem' },
  title: { fontSize: '2rem', color: '#1a1a2e', marginBottom: '0.5rem' },
  subtitle: { color: '#666', fontSize: '1.1rem', marginBottom: '1.5rem' },
  welcome: { color: '#4caf50', fontWeight: 'bold', fontSize: '1.1rem' },
  ctaButtons: { display: 'flex', gap: '1rem', justifyContent: 'center' },
  primaryBtn: { background: '#1a1a2e', color: 'white', padding: '0.75rem 2rem', borderRadius: '4px', textDecoration: 'none', fontWeight: 'bold' },
  secondaryBtn: { background: 'transparent', color: '#1a1a2e', padding: '0.75rem 2rem', borderRadius: '4px', textDecoration: 'none', border: '2px solid #1a1a2e', fontWeight: 'bold' },
  conceptGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' },
  conceptCard: { background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  conceptTitle: { color: '#1a1a2e', marginBottom: '0.5rem' },
  conceptDesc: { color: '#888', fontSize: '0.9rem', marginBottom: '0.75rem', fontStyle: 'italic' },
  list: { paddingLeft: '1.25rem', color: '#555', fontSize: '0.9rem', lineHeight: '1.8' },
  accessMatrix: { background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '2rem' },
  matrixTitle: { color: '#1a1a2e', marginBottom: '1rem', fontSize: '1.3rem' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { background: '#1a1a2e', color: 'white', padding: '0.6rem 1rem', textAlign: 'left', fontSize: '0.9rem' },
  td: { padding: '0.6rem 1rem', borderBottom: '1px solid #eee', fontSize: '0.9rem' },
  center: { textAlign: 'center' },
  trySection: { marginBottom: '2rem' },
  tryGrid: { display: 'flex', gap: '1rem', flexWrap: 'wrap' },
  tryCard: { background: 'white', padding: '1rem 1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', textDecoration: 'none', color: '#1a1a2e', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '500' },
  adminCard: { background: '#fff3e0', borderColor: '#ff9800' },
  tryIcon: { fontSize: '1.3rem' },
}
