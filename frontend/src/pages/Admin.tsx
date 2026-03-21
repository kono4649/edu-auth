/**
 * 管理者ページ
 *
 * PrivateRoute で requireAdmin=true に設定。
 * 管理者でないユーザーは /forbidden にリダイレクトされる。
 */
import { useState, useEffect } from 'react'
import { adminApi, type User } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export function Admin() {
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const { user: currentUser } = useAuth()

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      const { data } = await adminApi.listUsers()
      setUsers(data)
    } catch {
      setMessage('ユーザーの取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await adminApi.updateRole(userId, newRole)
      setMessage('ロールを更新しました')
      loadUsers()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '更新に失敗しました'
      setMessage(msg)
    }
  }

  const handleDeactivate = async (userId: number) => {
    if (!confirm('このユーザーを無効化しますか？')) return
    try {
      await adminApi.deactivateUser(userId)
      setMessage('ユーザーを無効化しました')
      loadUsers()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作に失敗しました'
      setMessage(msg)
    }
  }

  if (isLoading) return <div style={styles.center}>読み込み中...</div>

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>管理者パネル</h1>
      <div style={styles.adminBanner}>
        管理者専用ページ - ロール変更やユーザー管理が可能です
      </div>

      {message && (
        <div style={styles.message} onClick={() => setMessage('')}>
          {message}
        </div>
      )}

      <h2 style={styles.sectionTitle}>ユーザー管理</h2>
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th>
              <th style={styles.th}>ユーザー名</th>
              <th style={styles.th}>メール</th>
              <th style={styles.th}>ロール</th>
              <th style={styles.th}>状態</th>
              <th style={styles.th}>操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} style={user.id === currentUser?.id ? styles.currentRow : {}}>
                <td style={styles.td}>{user.id}</td>
                <td style={styles.td}>
                  {user.username}
                  {user.id === currentUser?.id && <span style={styles.selfBadge}> (自分)</span>}
                </td>
                <td style={styles.td}>{user.email}</td>
                <td style={styles.td}>
                  <select
                    value={user.role}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                    style={styles.roleSelect}
                    disabled={user.id === currentUser?.id}
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td style={styles.td}>
                  <span style={user.is_active ? styles.activeBadge : styles.inactiveBadge}>
                    {user.is_active ? '有効' : '無効'}
                  </span>
                </td>
                <td style={styles.td}>
                  {user.id !== currentUser?.id && user.is_active && (
                    <button onClick={() => handleDeactivate(user.id)} style={styles.deactivateBtn}>
                      無効化
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '2rem', maxWidth: '900px', margin: '0 auto' },
  center: { textAlign: 'center', padding: '2rem' },
  title: { color: '#1a1a2e', marginBottom: '0.5rem' },
  adminBanner: { background: '#fff3e0', border: '1px solid #ff9800', padding: '0.75rem', borderRadius: '4px', marginBottom: '1.5rem', color: '#e65100' },
  message: { background: '#e8f5e9', color: '#2e7d32', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem', cursor: 'pointer' },
  sectionTitle: { color: '#333', marginBottom: '1rem', fontSize: '1.2rem' },
  tableWrapper: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', background: 'white', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderRadius: '8px', overflow: 'hidden' },
  th: { background: '#1a1a2e', color: 'white', padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.9rem' },
  td: { padding: '0.75rem 1rem', borderBottom: '1px solid #eee', fontSize: '0.9rem' },
  currentRow: { background: '#f0f4ff' },
  selfBadge: { color: '#888', fontSize: '0.8rem' },
  roleSelect: { padding: '0.25rem', border: '1px solid #ddd', borderRadius: '4px' },
  activeBadge: { background: '#e8f5e9', color: '#2e7d32', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' },
  inactiveBadge: { background: '#fce4ec', color: '#c62828', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' },
  deactivateBtn: { background: '#e53935', color: 'white', border: 'none', padding: '0.3rem 0.6rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' },
}
