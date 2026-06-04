"""
注文エンドポイント

認可レベル:
- GET  /orders        : 管理者=全件, ユーザー=自分の注文のみ
- GET  /orders/{id}   : 管理者=全件, ユーザー=自分の注文のみ（他人のは403）
- POST /orders        : 認証済みユーザーのみ
- PUT  /orders/{id}/status : 管理者のみ

【学習ポイント】
同じエンドポイントでも、ロールによって見えるデータを変える「データレベルの認可」
"""
from __future__ import annotations

from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_roles, get_current_user, require_admin
from app.models import Order, OrderItem, Product, UserRole
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["注文"])


def _parse_user_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gateway ユーザーIDが UUID ではありません",
        ) from exc


@router.get("", response_model=List[OrderResponse])
def list_orders(
    current_user_id: str = Depends(get_current_user),
    roles: List[str] = Depends(get_current_roles),
    db: Session = Depends(get_db),
):
    """
    注文一覧取得

    【認可ロジック】
    - 管理者: 全ユーザーの注文を返す
    - 一般ユーザー: 自分の注文のみ返す

    これが「リソースレベルの認可」
    """
    if UserRole.ADMIN.value in roles:
        return db.query(Order).all()
    return db.query(Order).filter(Order.user_id == _parse_user_uuid(current_user_id)).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    current_user_id: str = Depends(get_current_user),
    roles: List[str] = Depends(get_current_roles),
    db: Session = Depends(get_db),
):
    """
    注文詳細取得

    【認可ロジック】
    - 管理者: どの注文でも閲覧可
    - 一般ユーザー: 他人の注文IDにアクセスすると403

    注意: 404ではなく403を返すことで、リソースの存在を漏らさない設計も考慮できる
    （ここでは学習目的で 403 を使用）
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="注文が見つかりません")

    # 自分の注文でも管理者でもない場合は403
    if UserRole.ADMIN.value not in roles and order.user_id != _parse_user_uuid(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この注文にアクセスする権限がありません",
        )

    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    注文作成（認証済みユーザーのみ）

    ゲスト（未認証）はアクセス不可。
    get_current_user が認証チェックを担当。
    """
    total = 0.0
    items = []

    for item_data in order_data.items:
        product = db.query(Product).filter(
            Product.id == item_data.product_id,
            Product.is_active == True,  # noqa: E712
        ).first()

        if not product:
            raise HTTPException(status_code=404, detail=f"商品 {item_data.product_id} が見つかりません")

        if product.stock < item_data.quantity:
            raise HTTPException(status_code=400, detail=f"商品 '{product.name}' の在庫が不足しています")

        total += product.price * item_data.quantity
        items.append((product, item_data.quantity))

    order = Order(user_id=_parse_user_uuid(current_user_id), total_amount=total)
    db.add(order)
    db.flush()

    for product, quantity in items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        )
        db.add(order_item)
        product.stock -= quantity

    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin_user_id: str = Depends(require_admin),
):
    """注文ステータス更新（管理者のみ）"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="注文が見つかりません")

    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order
