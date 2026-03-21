/**
 * 商品一覧ページ
 *
 * 認証不要で閲覧可能（パブリックページ）。
 * 管理者の場合は商品の追加・編集・削除ボタンが表示される。
 */
import { useState, useEffect } from 'react'
import { productsApi, ordersApi, type Product } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [cart, setCart] = useState<{ [id: number]: number }>({})
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const { isAdmin, isAuthenticated } = useAuth()

  // 管理者用: 商品追加フォーム
  const [showAddForm, setShowAddForm] = useState(false)
  const [newProduct, setNewProduct] = useState({ name: '', description: '', price: 0, stock: 0 })

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      const { data } = await productsApi.list()
      setProducts(data)
    } finally {
      setIsLoading(false)
    }
  }

  const addToCart = (productId: number) => {
    setCart((prev) => ({ ...prev, [productId]: (prev[productId] || 0) + 1 }))
  }

  const removeFromCart = (productId: number) => {
    setCart((prev) => {
      const next = { ...prev }
      if (next[productId] > 1) next[productId]--
      else delete next[productId]
      return next
    })
  }

  const checkout = async () => {
    if (!isAuthenticated) {
      setMessage('注文するにはログインが必要です')
      return
    }
    const items = Object.entries(cart).map(([id, qty]) => ({
      product_id: Number(id),
      quantity: qty,
    }))
    if (items.length === 0) {
      setMessage('カートが空です')
      return
    }
    try {
      await ordersApi.create(items)
      setCart({})
      setMessage('注文が完了しました！')
      loadProducts()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '注文に失敗しました'
      setMessage(msg)
    }
  }

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await productsApi.create(newProduct)
      setShowAddForm(false)
      setNewProduct({ name: '', description: '', price: 0, stock: 0 })
      loadProducts()
      setMessage('商品を追加しました')
    } catch {
      setMessage('商品の追加に失敗しました')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('この商品を削除しますか？')) return
    try {
      await productsApi.delete(id)
      loadProducts()
      setMessage('商品を削除しました')
    } catch {
      setMessage('削除に失敗しました')
    }
  }

  const cartTotal = Object.entries(cart).reduce((sum, [id, qty]) => {
    const product = products.find((p) => p.id === Number(id))
    return sum + (product?.price || 0) * qty
  }, 0)

  if (isLoading) return <div style={styles.center}>読み込み中...</div>

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>商品一覧</h1>
        {isAdmin && (
          <button onClick={() => setShowAddForm(!showAddForm)} style={styles.addButton}>
            + 商品を追加
          </button>
        )}
      </div>

      {message && (
        <div style={styles.message} onClick={() => setMessage('')}>
          {message}
        </div>
      )}

      {/* 管理者用: 商品追加フォーム */}
      {isAdmin && showAddForm && (
        <div style={styles.formCard}>
          <h3>新商品追加（管理者のみ）</h3>
          <form onSubmit={handleAddProduct} style={styles.form}>
            <input placeholder="商品名" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} style={styles.input} required />
            <input placeholder="説明" value={newProduct.description} onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })} style={styles.input} />
            <input type="number" placeholder="価格" value={newProduct.price} onChange={(e) => setNewProduct({ ...newProduct, price: Number(e.target.value) })} style={styles.input} required />
            <input type="number" placeholder="在庫数" value={newProduct.stock} onChange={(e) => setNewProduct({ ...newProduct, stock: Number(e.target.value) })} style={styles.input} required />
            <button type="submit" style={styles.submitButton}>追加する</button>
          </form>
        </div>
      )}

      <div style={styles.grid}>
        {products.map((product) => (
          <div key={product.id} style={styles.card}>
            <h3 style={styles.productName}>{product.name}</h3>
            {product.description && <p style={styles.description}>{product.description}</p>}
            <p style={styles.price}>¥{product.price.toLocaleString()}</p>
            <p style={styles.stock}>在庫: {product.stock}</p>

            <div style={styles.actions}>
              {!isAdmin && (
                <div style={styles.cartControls}>
                  {cart[product.id] ? (
                    <>
                      <button onClick={() => removeFromCart(product.id)} style={styles.cartBtn}>−</button>
                      <span style={styles.qty}>{cart[product.id]}</span>
                      <button onClick={() => addToCart(product.id)} style={styles.cartBtn} disabled={product.stock <= (cart[product.id] || 0)}>+</button>
                    </>
                  ) : (
                    <button onClick={() => addToCart(product.id)} style={styles.buyButton} disabled={product.stock === 0}>
                      {product.stock === 0 ? '在庫切れ' : 'カートに追加'}
                    </button>
                  )}
                </div>
              )}
              {isAdmin && (
                <button onClick={() => handleDelete(product.id)} style={styles.deleteButton}>
                  削除
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* カート */}
      {Object.keys(cart).length > 0 && (
        <div style={styles.cartBar}>
          <span>カート: {Object.values(cart).reduce((a, b) => a + b, 0)}点 合計: ¥{cartTotal.toLocaleString()}</span>
          <button onClick={checkout} style={styles.checkoutButton}>注文する</button>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '2rem', maxWidth: '1200px', margin: '0 auto' },
  center: { textAlign: 'center', padding: '2rem' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
  title: { color: '#1a1a2e' },
  addButton: { background: '#1a1a2e', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' },
  message: { background: '#e8f5e9', color: '#2e7d32', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem', cursor: 'pointer' },
  formCard: { background: '#f5f5f5', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' },
  form: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' },
  input: { padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', flex: '1', minWidth: '150px' },
  submitButton: { background: '#4caf50', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1.5rem' },
  card: { background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  productName: { marginBottom: '0.5rem', color: '#1a1a2e' },
  description: { color: '#666', fontSize: '0.9rem', marginBottom: '0.5rem' },
  price: { fontSize: '1.3rem', fontWeight: 'bold', color: '#e53935', marginBottom: '0.25rem' },
  stock: { fontSize: '0.85rem', color: '#888', marginBottom: '1rem' },
  actions: { display: 'flex', justifyContent: 'center' },
  cartControls: { display: 'flex', alignItems: 'center', gap: '0.5rem' },
  cartBtn: { background: '#f0f0f0', border: '1px solid #ddd', width: '28px', height: '28px', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem' },
  qty: { fontWeight: 'bold', minWidth: '24px', textAlign: 'center' },
  buyButton: { background: '#1a1a2e', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', width: '100%' },
  deleteButton: { background: '#e53935', color: 'white', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '4px', cursor: 'pointer' },
  cartBar: { position: 'fixed', bottom: '1rem', right: '1rem', background: '#1a1a2e', color: 'white', padding: '1rem 1.5rem', borderRadius: '8px', display: 'flex', gap: '1rem', alignItems: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.3)' },
  checkoutButton: { background: '#ffd700', color: '#1a1a2e', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' },
}
