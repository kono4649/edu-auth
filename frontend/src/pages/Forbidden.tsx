import { Link } from 'react-router-dom'

export function Forbidden() {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.code}>403</h1>
        <h2 style={styles.title}>アクセス権限がありません</h2>
        <p style={styles.description}>
          このページは管理者のみアクセスできます。<br />
          管理者アカウントでログインしてください。
        </p>
        <Link to="/" style={styles.link}>トップページへ戻る</Link>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' },
  card: { textAlign: 'center', padding: '2rem' },
  code: { fontSize: '6rem', color: '#e53935', margin: '0' },
  title: { color: '#1a1a2e', marginBottom: '1rem' },
  description: { color: '#666', lineHeight: '1.8', marginBottom: '1.5rem' },
  link: { background: '#1a1a2e', color: 'white', padding: '0.75rem 2rem', borderRadius: '4px', textDecoration: 'none' },
}
