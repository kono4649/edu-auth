"""
商品エンドポイント

認可レベル:
- GET  /products      : 誰でも閲覧可（認証不要）
- GET  /products/{id} : 誰でも閲覧可（認証不要）
- POST /products      : 管理者のみ（require_admin）
- PUT  /products/{id} : 管理者のみ（require_admin）
- DELETE /products/{id}: 管理者のみ（require_admin）
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["商品"])


@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """
    商品一覧取得（認証不要・公開エンドポイント）
    アクティブな商品のみ返す
    """
    return db.query(Product).filter(Product.is_active == True).all()  # noqa: E712


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """商品詳細取得（認証不要・公開エンドポイント）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品が見つかりません")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    admin_user_id: str = Depends(require_admin),
):
    """
    商品作成（管理者のみ）

    require_admin 依存関係が認可チェックを行う:
    1. JWT トークンで認証（Authentication）
    2. role == "admin" を確認（Authorization）
    """
    product = Product(**product_data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    admin_user_id: str = Depends(require_admin),
):
    """商品更新（管理者のみ）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品が見つかりません")

    for field, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin_user_id: str = Depends(require_admin),
):
    """商品削除（管理者のみ）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品が見つかりません")

    db.delete(product)
    db.commit()
