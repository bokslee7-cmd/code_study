import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, String, Table
from sqlalchemy.dialects.postgresql import UUID
from src.models import User
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _table() -> Table:
    table = User.__table__
    assert isinstance(table, Table)
    return table


def test_user_is_registered_on_base_metadata():
    assert issubclass(User, Base)
    assert Base.metadata.tables["users"] is _table()


def test_user_reuses_standard_mixins():
    assert issubclass(User, UUIDPrimaryKeyMixin)
    assert issubclass(User, TimestampMixin)


def test_user_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "email",
        "password_hash",
        "skill_level",
        "created_at",
        "updated_at",
        "last_login_at",
    }


def test_user_column_types_and_lengths():
    columns = _table().c
    assert isinstance(columns.id.type, UUID)
    assert isinstance(columns.email.type, String) and columns.email.type.length == 255
    assert isinstance(columns.password_hash.type, String)
    assert columns.password_hash.type.length == 255
    assert isinstance(columns.skill_level.type, String) and columns.skill_level.type.length == 50
    for name in ("created_at", "updated_at", "last_login_at"):
        column_type = columns[name].type
        assert isinstance(column_type, DateTime) and column_type.timezone


def test_user_nullability():
    columns = _table().c
    assert columns.id.primary_key
    assert not columns.email.nullable
    assert not columns.password_hash.nullable
    assert columns.last_login_at.nullable


def test_email_is_unique():
    assert _table().c.email.unique


def test_skill_level_defaults_to_complete_beginner():
    default = _table().c.skill_level.server_default
    assert default is not None
    assert "Complete Beginner" in str(default.arg)


def test_email_index_matches_migration():
    index_names = {index.name: [c.name for c in index.columns] for index in _table().indexes}
    assert index_names["idx_users_email"] == ["email"]


def test_valid_email_check_constraint_keeps_migration_name():
    checks = {c.name: c for c in _table().constraints if isinstance(c, CheckConstraint)}
    assert "valid_email" in checks
    assert "email" in str(checks["valid_email"].sqltext)


def test_user_can_be_built_with_required_fields_only():
    user = User(email="learner@example.com", password_hash="hashed")
    assert user.email == "learner@example.com"
    assert user.password_hash == "hashed"
    assert user.last_login_at is None


def test_user_accepts_explicit_values():
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="a@b.com",
        password_hash="h",
        skill_level="Intermediate",
        last_login_at=now,
    )
    assert user.id == user_id
    assert user.skill_level == "Intermediate"
    assert user.last_login_at == now


def test_repr_never_exposes_password_hash():
    user = User(email="learner@example.com", password_hash="super-secret-hash")
    text = repr(user)
    assert "learner@example.com" in text
    assert "super-secret-hash" not in text
