import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers
from src.models import Project, Task
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _table() -> Table:
    table = Task.__table__
    assert isinstance(table, Table)
    return table


def test_task_is_registered_on_base_metadata():
    assert issubclass(Task, Base)
    assert issubclass(Task, UUIDPrimaryKeyMixin)
    assert issubclass(Task, TimestampMixin)
    assert Base.metadata.tables["tasks"] is _table()


def test_task_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "project_id",
        "task_number",
        "title",
        "description",
        "upload_method",
        "created_at",
        "updated_at",
        "deletion_status",
        "trashed_at",
        "scheduled_deletion_at",
    }


def test_task_column_types():
    columns = _table().c
    assert isinstance(columns.id.type, UUID)
    assert isinstance(columns.project_id.type, UUID)
    assert isinstance(columns.task_number.type, Integer)
    assert isinstance(columns.title.type, String) and columns.title.type.length == 255
    assert isinstance(columns.description.type, Text)
    assert isinstance(columns.upload_method.type, String)
    assert columns.upload_method.type.length == 20
    assert isinstance(columns.deletion_status.type, String)
    assert columns.deletion_status.type.length == 20
    for name in ("created_at", "updated_at", "trashed_at", "scheduled_deletion_at"):
        column_type = columns[name].type
        assert isinstance(column_type, DateTime) and column_type.timezone


def test_task_nullability():
    columns = _table().c
    assert not columns.project_id.nullable
    assert not columns.task_number.nullable
    assert not columns.title.nullable
    assert not columns.deletion_status.nullable
    assert columns.description.nullable
    assert columns.upload_method.nullable
    assert columns.trashed_at.nullable
    assert columns.scheduled_deletion_at.nullable


def test_project_id_references_projects_with_cascade_delete():
    foreign_keys = list(_table().c.project_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "projects.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_deletion_status_defaults_to_active_in_db_and_python():
    status = _table().c.deletion_status
    assert status.server_default is not None
    assert "active" in str(status.server_default.arg)
    assert status.default is not None and status.default.arg == "active"


def test_check_constraints_keep_the_migration_names():
    checks = {
        c.name: str(c.sqltext) for c in _table().constraints if isinstance(c, CheckConstraint)
    }
    assert "char_length(title) >= 5" in checks["title_min_length"]
    assert "char_length(description) <= 500" in checks["description_max_length"]
    status_check = checks["tasks_deletion_status_check"]
    assert "'active'" in status_check and "'trashed'" in status_check
    upload_check = checks["tasks_upload_method_check"]
    for method in ("'file'", "'folder'", "'paste'"):
        assert method in upload_check


def test_task_number_is_unique_per_project():
    uniques = {c.name: c for c in _table().constraints if isinstance(c, UniqueConstraint)}
    unique = uniques["unique_task_number_per_project"]
    assert [c.name for c in unique.columns] == ["project_id", "task_number"]


def test_indexes_match_migration():
    indexes = {index.name: index for index in _table().indexes}
    assert [c.name for c in indexes["idx_tasks_project_id"].columns] == ["project_id"]
    assert [c.name for c in indexes["idx_tasks_deletion_status"].columns] == ["deletion_status"]
    assert [c.name for c in indexes["idx_tasks_number_order"].columns] == [
        "project_id",
        "task_number",
    ]
    partial = indexes["idx_tasks_project_active"]
    assert [c.name for c in partial.columns] == ["project_id", "deletion_status"]
    where = partial.dialect_options["postgresql"]["where"]
    assert "deletion_status = 'active'" in str(where)


def test_task_can_be_built_with_required_fields_only():
    project_id = uuid.uuid4()
    task = Task(project_id=project_id, task_number=1, title="로그인 기능 분석")
    assert task.project_id == project_id
    assert task.task_number == 1
    assert task.title == "로그인 기능 분석"
    assert task.description is None
    assert task.upload_method is None
    assert task.trashed_at is None
    assert task.scheduled_deletion_at is None


def test_constants():
    assert Task.ACTIVE == "active"
    assert Task.TRASHED == "trashed"
    assert Task.UPLOAD_METHODS == ("file", "folder", "paste")


def test_soft_delete_fields_can_be_set():
    trashed_at = datetime.now(UTC)
    task = Task(
        project_id=uuid.uuid4(),
        task_number=2,
        title="soft delete",
        deletion_status=Task.TRASHED,
        trashed_at=trashed_at,
        scheduled_deletion_at=trashed_at + timedelta(days=30),
    )
    assert task.deletion_status == "trashed"
    assert task.scheduled_deletion_at - task.trashed_at == timedelta(days=30)


def test_project_and_task_are_linked_both_ways():
    configure_mappers()
    project = Project(title="p")
    task = Task(task_number=1, title="첫 번째 태스크", project=project)
    assert task.project is project
    assert project.tasks == [task]


def test_deleting_project_is_left_to_database_cascade():
    relationship = Project.__mapper__.relationships["tasks"]
    assert relationship.passive_deletes is True
    assert relationship.back_populates == "project"


def test_repr_shows_id_number_title_and_status():
    status = Task.TRASHED
    task = Task(project_id=uuid.uuid4(), task_number=3, title="내 태스크", deletion_status=status)
    text = repr(task)
    assert "3" in text and "내 태스크" in text and "trashed" in text
