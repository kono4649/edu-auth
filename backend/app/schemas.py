"""
Pydantic スキーマ定義
リクエスト/レスポンスのバリデーションと型定義
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from app.models import UserRole, OrderStatus


# ─── 認証関連スキーマ ───────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    """ユーザー登録リクエスト"""
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    """ログインリクエスト"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    トークンレスポンス
    - access_token: APIアクセスに使う短命トークン（30分）
    - refresh_token: アクセストークン更新に使う長命トークン（7日）
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """トークンリフレッシュリクエスト"""
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """新しいアクセストークンのみのレスポンス"""
    access_token: str
    token_type: str = "bearer"


# ─── ユーザー関連スキーマ ──────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """ユーザー情報レスポンス（パスワードは含まない）"""
    id: int
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 商品関連スキーマ ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    """商品作成リクエスト（管理者のみ）"""
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0


class ProductUpdate(BaseModel):
    """商品更新リクエスト（管理者のみ）"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    """商品情報レスポンス"""
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 注文関連スキーマ ──────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    """注文明細作成リクエスト"""
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    """注文作成リクエスト（認証済みユーザーのみ）"""
    items: List[OrderItemCreate]


class OrderItemResponse(BaseModel):
    """注文明細レスポンス"""
    id: int
    product_id: int
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """注文情報レスポンス"""
    id: int
    user_id: int
    status: OrderStatus
    total_amount: float
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    """注文ステータス更新（管理者のみ）"""
    status: OrderStatus


# ─── 管理者向けスキーマ ─────────────────────────────────────────────────────────

class UserRoleUpdate(BaseModel):
    """ユーザーロール変更（管理者のみ）"""
    role: UserRole
