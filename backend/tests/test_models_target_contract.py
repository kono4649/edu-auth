import uuid


def test_user_model_has_no_password_or_active_fields():
    from app.models import User

    column_names = set(User.__table__.columns.keys())

    assert "hashed_password" not in column_names
    assert "is_active" not in column_names


def test_user_model_uses_uuid_id_and_default_user_role():
    from app.models import User, UserRole

    id_column = User.__table__.columns["id"]
    role_column = User.__table__.columns["role"]

    assert id_column.type.python_type is uuid.UUID
    assert role_column.default is not None
    assert role_column.default.arg == UserRole.USER


def test_refresh_token_model_has_been_removed():
    import app.models as models

    assert not hasattr(models, "RefreshToken")
