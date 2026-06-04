import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

export function Login() {
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()

  const handleLogin = async () => {
    setError('')
    setIsLoading(true)
    try {
      await login()
    } catch {
      setError('IdP へのリダイレクトに失敗しました')
      setIsLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>ログイン</h2>

        {error && <div style={styles.error}>{error}</div>}

        <button type="button" style={styles.button} onClick={handleLogin} disabled={isLoading}>
          {isLoading ? '処理中...' : 'IdP でログイン'}
        </button>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', padding: '2rem' },
  card: { background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', width: '100%', maxWidth: '400px' },
  title: { marginBottom: '1.5rem', color: '#1a1a2e', textAlign: 'center' },
  error: { background: '#ffebee', color: '#c62828', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem' },
  button: { width: '100%', padding: '0.75rem', background: '#1a1a2e', color: 'white', border: 'none', borderRadius: '4px', fontSize: '1rem', cursor: 'pointer' },
}
