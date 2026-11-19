import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import CheckConstraint, DateTime, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers
from src.models import Project, User
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _table() -> Table:
    table = Project.__table__
    assert isinstance(table, Table)
    return table


def test_project_is_registered_on_base_metadata():
    assert issubclass(Project, Base)
    assert issubclass(Project, UUIDPrimaryKeyMixin)
    assert issubclass(Project, TimestampMixin)
    assert Base.metadata.tables["projects"] is _table()


def test_project_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "user_id",
        "title",
        "description",
        "created_at",
        "updated_at",
        "last_activity_at",
        "deletion_status",
        "trashed_at",
        "scheduled_deletion_at",
    }


def test_project_column_types():
    columns = _table().c
    assert isinstance(columns.id.type, UUID)
    assert isinstance(columns.user_id.type, UUID)
    assert isinstance(columns.title.type, String) and columns.title.type.length == 255
    assert isinstance(columns.description.type, Text)
    assert isinstance(columns.deletion_status.type, String)
    assert columns.deletion_status.type.length == 20
    for name in (
        "created_at",
        "updated_at",
        "last_activity_at",
        "trashed_at",
        "scheduled_deletion_at",
    ):
        column_type = columns[name].type
        assert isinstance(column_type, DateTime) and column_type.timezone


def test_project_nullability():
    columns = _table().c
    assert not columns.user_id.nullable
    assert not columns.title.nullable
    assert not columns.deletion_status.nullable
    assert columns.description.nullable
    assert columns.trashed_at.nullable
    assert columns.scheduled_deletion_at.nullable


def test_user_id_references_users_with_cascade_delete():
    foreign_keys = list(_table().c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_timestamps_are_filled_by_the_database():
    columns = _table().c
    for name in ("created_at", "updated_at", "last_activity_at"):
        assert columns[name].server_default is not None, name


def test_deletion_status_defaults_to_active_in_db_and_python():
    status = _table().c.deletion_status
    assert status.server_default is not None
    assert "active" in str(status.server_default.arg)
    assert status.default is not None and status.default.arg == "active"


def test_check_constraints_keep_the_migration_names():
    checks = {
        c.name: str(c.sqltext) for c in _table().constraints if isinstance(c, CheckConstraint)
    }
    assert "char_length(title) >= 1" in checks["title_min_length"]
    status_check = checks["projects_deletion_status_check"]
    assert "'active'" in status_check and "'trashed'" in status_check


def test_indexes_match_migration():
    indexes = {index.name: index for index in _table().indexes}
    assert [c.name for c in indexes["idx_projects_user_id"].columns] == ["user_id"]
    assert [c.name for c in indexes["idx_projects_deletion_status"].columns] == ["deletion_status"]
    partial = indexes["idx_projects_user_active"]
    assert [c.name for c in partial.columns] == ["user_id", "deletion_status"]
    where = partial.dialect_options["postgresql"]["where"]
    assert "deletion_status = 'active'" in str(where)


def test_project_can_be_built_with_required_fields_only():
    user_id = uuid.uuid4()
    project = Project(user_id=user_id, title="내 첫 프로젝트")
    assert project.user_id == user_id
    assert project.title == "내 첫 프로젝트"
    assert project.description is None
    assert project.trashed_at is None
    assert project.scheduled_deletion_at is None


def test_deletion_status_constants():
    assert Project.ACTIVE == "active"
    assert Project.TRASHED == "trashed"


def test_soft_delete_fields_can_be_set():
    trashed_at = datetime.now(UTC)
    project = Project(
        user_id=uuid.uuid4(),
        title="p",
        deletion_status=Project.TRASHED,
        trashed_at=trashed_at,
        scheduled_deletion_at=trashed_at + timedelta(days=30),
    )
    assert project.deletion_status == "trashed"
    assert project.scheduled_deletion_at - project.trashed_at == timedelta(days=30)


def test_user_and_project_are_linked_both_ways():
    configure_mappers()
    user = User(email="a@b.com", password_hash="h")
    project = Project(title="p", user=user)
    assert project.user is user
    assert user.projects == [project]


def test_deleting_user_is_left_to_database_cascade():
    relationship = User.__mapper__.relationships["projects"]
    assert relationship.passive_deletes is True
    assert relationship.back_populates == "user"


def test_repr_shows_id_title_and_status():
    project = Project(user_id=uuid.uuid4(), title="내 프로젝트", deletion_status=Project.TRASHED)
    text = repr(project)
    assert "내 프로젝트" in text and "trashed" in text
