import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // ログイン前にアクセスしようとしていたページへリダイレクト
  const from = (location.state as { from?: Location })?.from?.pathname || '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'ログインに失敗しました'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>ログイン</h2>

        <div style={styles.hint}>
          <p style={styles.hintTitle}>テストアカウント</p>
          <p>管理者: admin@example.com / admin123</p>
          <p>一般: user@example.com / user123</p>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>メールアドレス</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
              required
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>パスワード</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              required
            />
          </div>
          <button type="submit" style={styles.button} disabled={isLoading}>
            {isLoading ? '処理中...' : 'ログイン'}
          </button>
        </form>

        <p style={styles.linkText}>
          アカウントをお持ちでない方は <Link to="/register">新規登録</Link>
        </p>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', padding: '2rem' },
  card: { background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', width: '100%', maxWidth: '400px' },
  title: { marginBottom: '1.5rem', color: '#1a1a2e', textAlign: 'center' },
  hint: { background: '#f0f4ff', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem', fontSize: '0.85rem', color: '#555' },
  hintTitle: { fontWeight: 'bold', marginBottom: '0.25rem', color: '#333' },
  error: { background: '#ffebee', color: '#c62828', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem' },
  form: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  field: { display: 'flex', flexDirection: 'column', gap: '0.25rem' },
  label: { fontSize: '0.9rem', fontWeight: '600', color: '#333' },
  input: { padding: '0.6rem', border: '1px solid #ddd', borderRadius: '4px', fontSize: '1rem' },
  button: { padding: '0.75rem', background: '#1a1a2e', color: 'white', border: 'none', borderRadius: '4px', fontSize: '1rem', cursor: 'pointer', marginTop: '0.5rem' },
  linkText: { textAlign: 'center', marginTop: '1rem', fontSize: '0.9rem', color: '#666' },
}
