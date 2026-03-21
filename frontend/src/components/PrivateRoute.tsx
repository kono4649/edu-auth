/**
 * プライベートルート コンポーネント
 *
 * 【学習ポイント: フロントエンドの認可】
 * React Router でルートへのアクセスをロールで制御する。
 *
 * 注意: フロントエンドの認可はUX目的（不要なページを隠す）。
 * セキュリティの本質はバックエンドの認可にある。
 * フロントエンドのチェックはユーザーが直接 API を叩けば迂回できる。
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface PrivateRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export function PrivateRoute({ children, requireAdmin = false }: PrivateRouteProps) {
  const { isAuthenticated, isAdmin, isLoading } = useAuth()
  const location = useLocation()

  // 認証状態の初期化中はローディング表示
  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: '2rem' }}>読み込み中...</div>
  }

  // 未認証 → ログインページへリダイレクト（元のURLを state に保存）
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 管理者が必要なページに一般ユーザーがアクセス → 403 ページへ
  if (requireAdmin && !isAdmin) {
    return <Navigate to="/forbidden" replace />
  }

  return <>{children}</>
}
