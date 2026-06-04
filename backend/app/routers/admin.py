"""管理者専用エンドポイント。"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas import UserResponse, UserRoleUpdate

router = APIRouter(prefix="/admin", tags=["管理者"])


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin_user_id: str = Depends(require_admin),
):
    """全ユーザー一覧（管理者のみ）"""
    return db.query(User).all()


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: uuid.UUID,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user_id: str = Depends(require_admin),
):
    """
    ユーザーロール変更（管理者のみ）

    管理者が一般ユーザーに管理者権限を付与、または剥奪できる。
    自分自身のロール変更は禁止（誤って管理者を失わないように）。
    """
    if str(user_id) == admin_user_id:
        raise HTTPException(status_code=400, detail="自分自身のロールは変更できません")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    user.role = role_update.role
    db.commit()
    db.refresh(user)
    return user
