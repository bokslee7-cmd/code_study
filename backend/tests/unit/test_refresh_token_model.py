import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Boolean, DateTime, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers
from src.models import RefreshToken, User
from src.models.base import Base, UUIDPrimaryKeyMixin


def _table() -> Table:
    table = RefreshToken.__table__
    assert isinstance(table, Table)
    return table


def test_refresh_token_is_registered_on_base_metadata():
    assert issubclass(RefreshToken, Base)
    assert issubclass(RefreshToken, UUIDPrimaryKeyMixin)
    assert Base.metadata.tables["refresh_tokens"] is _table()


def test_refresh_token_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "user_id",
        "token_hash",
        "expires_at",
        "created_at",
        "revoked",
        "revoked_at",
    }


def test_refresh_token_column_types():
    columns = _table().c
    assert isinstance(columns.id.type, UUID)
    assert isinstance(columns.user_id.type, UUID)
    assert isinstance(columns.token_hash.type, String) and columns.token_hash.type.length == 255
    assert isinstance(columns.revoked.type, Boolean)
    for name in ("expires_at", "created_at", "revoked_at"):
        column_type = columns[name].type
        assert isinstance(column_type, DateTime) and column_type.timezone


def test_refresh_token_nullability():
    columns = _table().c
    assert not columns.user_id.nullable
    assert not columns.token_hash.nullable
    assert not columns.expires_at.nullable
    assert columns.revoked_at.nullable


def test_token_hash_is_unique():
    assert _table().c.token_hash.unique


def test_user_id_references_users_with_cascade_delete():
    foreign_keys = list(_table().c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_indexes_match_migration():
    indexes = {index.name: [c.name for c in index.columns] for index in _table().indexes}
    assert indexes["idx_refresh_tokens_user_id"] == ["user_id"]
    assert indexes["idx_refresh_tokens_hash"] == ["token_hash"]
    assert indexes["idx_refresh_tokens_expires"] == ["expires_at"]


def test_created_at_has_server_default_and_no_updated_at():
    columns = _table().c
    assert columns.created_at.server_default is not None
    assert "updated_at" not in columns


def test_revoked_defaults_to_false_in_db_and_python():
    revoked = _table().c.revoked
    assert not revoked.nullable
    assert revoked.server_default is not None
    assert "false" in str(revoked.server_default.arg).lower()
    assert revoked.default is not None and revoked.default.arg is False


def test_refresh_token_can_be_built_with_required_fields_only():
    user_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=7)
    token = RefreshToken(user_id=user_id, token_hash="a" * 64, expires_at=expires_at)
    assert token.user_id == user_id
    assert token.expires_at == expires_at
    assert token.revoked_at is None


def test_user_and_refresh_token_are_linked_both_ways():
    configure_mappers()
    user = User(email="a@b.com", password_hash="h")
    token = RefreshToken(token_hash="t", expires_at=datetime.now(UTC), user=user)
    assert token.user is user
    assert user.refresh_tokens == [token]


def test_deleting_user_is_left_to_database_cascade():
    relationship = User.__mapper__.relationships["refresh_tokens"]
    assert relationship.passive_deletes is True
    assert relationship.back_populates == "user"


def test_repr_never_exposes_token_hash():
    token = RefreshToken(token_hash="secret-token-hash", expires_at=datetime.now(UTC))
    assert "secret-token-hash" not in repr(token)
