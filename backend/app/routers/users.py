"""ユーザー本人情報エンドポイント。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, parse_gateway_user_uuid
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["ユーザー"])


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == parse_gateway_user_uuid(current_user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません")
    return user
