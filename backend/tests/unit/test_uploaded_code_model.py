import uuid

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers
from src.models import Task, UploadedCode
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

MAX_UPLOAD_BYTES = 10485760


def _table() -> Table:
    table = UploadedCode.__table__
    assert isinstance(table, Table)
    return table


def test_uploaded_code_is_registered_on_base_metadata():
    assert issubclass(UploadedCode, Base)
    assert issubclass(UploadedCode, UUIDPrimaryKeyMixin)
    assert Base.metadata.tables["uploaded_code"] is _table()


def test_table_has_no_updated_at_so_timestamp_mixin_is_not_used():
    assert not issubclass(UploadedCode, TimestampMixin)


def test_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "task_id",
        "detected_language",
        "complexity_level",
        "total_lines",
        "total_files",
        "upload_size_bytes",
        "created_at",
    }


def test_column_types():
    columns = _table().c
    assert isinstance(columns.id.type, UUID)
    assert isinstance(columns.task_id.type, UUID)
    assert isinstance(columns.detected_language.type, String)
    assert columns.detected_language.type.length == 50
    assert isinstance(columns.complexity_level.type, String)
    assert columns.complexity_level.type.length == 20
    for name in ("total_lines", "total_files", "upload_size_bytes"):
        assert isinstance(columns[name].type, Integer), name
    assert isinstance(columns.created_at.type, DateTime) and columns.created_at.type.timezone


def test_nullability():
    columns = _table().c
    assert not columns.task_id.nullable
    for name in (
        "detected_language",
        "complexity_level",
        "total_lines",
        "total_files",
        "upload_size_bytes",
    ):
        assert columns[name].nullable, name


def test_created_at_is_filled_by_the_database():
    assert _table().c.created_at.server_default is not None


def test_task_id_references_tasks_with_cascade_delete():
    foreign_keys = list(_table().c.task_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "tasks.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_task_id_is_unique_with_the_migration_constraint_name():
    uniques = {c.name: c for c in _table().constraints if isinstance(c, UniqueConstraint)}
    assert [c.name for c in uniques["uploaded_code_task_id_key"].columns] == ["task_id"]


def test_check_constraints_keep_the_migration_names():
    checks = {
        c.name: str(c.sqltext) for c in _table().constraints if isinstance(c, CheckConstraint)
    }
    level_check = checks["uploaded_code_complexity_level_check"]
    for level in ("'beginner'", "'intermediate'", "'advanced'"):
        assert level in level_check
    assert str(MAX_UPLOAD_BYTES) in checks["valid_upload_size"]


def test_task_id_index_matches_migration():
    indexes = {index.name: index for index in _table().indexes}
    assert [c.name for c in indexes["idx_uploaded_code_task_id"].columns] == ["task_id"]


def test_can_be_built_with_required_fields_only():
    task_id = uuid.uuid4()
    uploaded = UploadedCode(task_id=task_id)
    assert uploaded.task_id == task_id
    assert uploaded.detected_language is None
    assert uploaded.complexity_level is None
    assert uploaded.total_lines is None
    assert uploaded.total_files is None
    assert uploaded.upload_size_bytes is None


def test_constants():
    assert UploadedCode.COMPLEXITY_LEVELS == ("beginner", "intermediate", "advanced")
    assert UploadedCode.MAX_UPLOAD_SIZE_BYTES == MAX_UPLOAD_BYTES


def test_task_and_uploaded_code_are_linked_one_to_one():
    configure_mappers()
    task = Task(project_id=uuid.uuid4(), task_number=1, title="첫 번째 태스크")
    uploaded = UploadedCode(task=task)
    assert uploaded.task is task
    assert task.uploaded_code is uploaded


def test_deleting_task_is_left_to_database_cascade():
    relationship = Task.__mapper__.relationships["uploaded_code"]
    assert relationship.uselist is False
    assert relationship.passive_deletes is True
    assert relationship.back_populates == "task"


def test_repr_shows_id_task_and_language():
    task_id = uuid.uuid4()
    text = repr(UploadedCode(task_id=task_id, detected_language="Python"))
    assert str(task_id) in text and "Python" in text
