/**
 * 注文履歴ページ
 *
 * 認証が必要なページ（PrivateRoute でガード）。
 * 一般ユーザーは自分の注文のみ、管理者は全ユーザーの注文を見られる。
 */
import { useState, useEffect } from 'react'
import { ordersApi, type Order } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const STATUS_LABELS: Record<string, string> = {
  pending: '受付中',
  confirmed: '確認済み',
  shipped: '発送済み',
  delivered: '配達完了',
  cancelled: 'キャンセル',
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#ff9800',
  confirmed: '#2196f3',
  shipped: '#9c27b0',
  delivered: '#4caf50',
  cancelled: '#9e9e9e',
}

export function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const { isAdmin } = useAuth()

  useEffect(() => {
    loadOrders()
  }, [])

  const loadOrders = async () => {
    try {
      const { data } = await ordersApi.list()
      setOrders(data)
    } catch {
      setMessage('注文の取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  const handleStatusUpdate = async (orderId: number, newStatus: string) => {
    try {
      await ordersApi.updateStatus(orderId, newStatus)
      setMessage('ステータスを更新しました')
      loadOrders()
    } catch {
      setMessage('更新に失敗しました')
    }
  }

  if (isLoading) return <div style={styles.center}>読み込み中...</div>

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>{isAdmin ? '全注文一覧（管理者）' : '注文履歴'}</h1>

      {message && (
        <div style={styles.message} onClick={() => setMessage('')}>
          {message}
        </div>
      )}

      {orders.length === 0 ? (
        <div style={styles.empty}>注文がありません</div>
      ) : (
        <div style={styles.list}>
          {orders.map((order) => (
            <div key={order.id} style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <span style={styles.orderId}>注文 #{order.id}</span>
                  {isAdmin && <span style={styles.userId}> ユーザーID: {order.user_id}</span>}
                </div>
                <div style={styles.statusArea}>
                  <span style={{ ...styles.statusBadge, background: STATUS_COLORS[order.status] }}>
                    {STATUS_LABELS[order.status]}
                  </span>
                  {/* 管理者のみステータス変更可能 */}
                  {isAdmin && (
                    <select
                      value={order.status}
                      onChange={(e) => handleStatusUpdate(order.id, e.target.value)}
                      style={styles.select}
                    >
                      {Object.entries(STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              <div style={styles.items}>
                {order.items.map((item) => (
                  <div key={item.id} style={styles.item}>
                    <span>商品 #{item.product_id} × {item.quantity}</span>
                    <span>¥{(item.unit_price * item.quantity).toLocaleString()}</span>
                  </div>
                ))}
              </div>

              <div style={styles.cardFooter}>
                <span style={styles.date}>{new Date(order.created_at).toLocaleString('ja-JP')}</span>
                <span style={styles.total}>合計: ¥{order.total_amount.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '2rem', maxWidth: '800px', margin: '0 auto' },
  center: { textAlign: 'center', padding: '2rem' },
  title: { color: '#1a1a2e', marginBottom: '1.5rem' },
  message: { background: '#e8f5e9', color: '#2e7d32', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem', cursor: 'pointer' },
  empty: { textAlign: 'center', padding: '3rem', color: '#888' },
  list: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  card: { background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' },
  orderId: { fontWeight: 'bold', color: '#1a1a2e', fontSize: '1.1rem' },
  userId: { fontSize: '0.85rem', color: '#888', marginLeft: '0.5rem' },
  statusArea: { display: 'flex', alignItems: 'center', gap: '0.5rem' },
  statusBadge: { color: 'white', padding: '0.2rem 0.6rem', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 'bold' },
  select: { padding: '0.25rem', border: '1px solid #ddd', borderRadius: '4px', fontSize: '0.85rem' },
  items: { borderTop: '1px solid #eee', borderBottom: '1px solid #eee', padding: '0.75rem 0', marginBottom: '0.75rem' },
  item: { display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', fontSize: '0.9rem', color: '#555' },
  cardFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  date: { fontSize: '0.85rem', color: '#888' },
  total: { fontWeight: 'bold', fontSize: '1.1rem', color: '#1a1a2e' },
}
