import uuid

import pytest


def test_update_user_role_rejects_self_change_with_compact_uppercase_gateway_user_id(user_id):
    from app.models import UserRole
    from app.routers.admin import update_user_role
    from app.schemas import UserRoleUpdate

    gateway_user_id = uuid.UUID(user_id).hex.upper()

    with pytest.raises(Exception) as exc_info:
        update_user_role(
            user_id=uuid.UUID(user_id),
            role_update=UserRoleUpdate(role=UserRole.USER),
            db=None,
            admin_user_id=gateway_user_id,
        )

    assert getattr(exc_info.value, "status_code", None) == 400
