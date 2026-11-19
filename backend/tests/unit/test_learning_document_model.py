import uuid

from sqlalchemy import CheckConstraint, DateTime, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import configure_mappers
from src.models import LearningDocument, Task
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _table() -> Table:
    table = LearningDocument.__table__
    assert isinstance(table, Table)
    return table


def test_learning_document_is_registered_on_base_metadata():
    assert issubclass(LearningDocument, Base)
    assert issubclass(LearningDocument, UUIDPrimaryKeyMixin)
    assert issubclass(LearningDocument, TimestampMixin)
    assert Base.metadata.tables["learning_documents"] is _table()


def test_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "task_id",
        "content",
        "generation_status",
        "generation_started_at",
        "generation_completed_at",
        "generation_error",
        "celery_task_id",
        "created_at",
        "updated_at",
    }


def test_column_types():
    columns = _table().c
    assert isinstance(columns.task_id.type, UUID)
    assert isinstance(columns.content.type, JSONB)
    assert isinstance(columns.generation_status.type, String)
    assert columns.generation_status.type.length == 20
    assert isinstance(columns.generation_error.type, Text)
    assert isinstance(columns.celery_task_id.type, String)
    assert columns.celery_task_id.type.length == 255
    for name in ("generation_started_at", "generation_completed_at"):
        assert isinstance(columns[name].type, DateTime) and columns[name].type.timezone, name


def test_nullability():
    columns = _table().c
    assert not columns.task_id.nullable
    assert not columns.content.nullable
    for name in (
        "generation_status",
        "generation_started_at",
        "generation_completed_at",
        "generation_error",
        "celery_task_id",
    ):
        assert columns[name].nullable, name  # 마이그레이션: DEFAULT 'pending'만 있고 NOT NULL 아님


def test_generation_status_defaults_to_pending_in_database():
    default = _table().c.generation_status.server_default
    assert default is not None and "pending" in str(default.arg)


def test_task_id_references_tasks_with_cascade_delete():
    foreign_keys = list(_table().c.task_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "tasks.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_task_id_is_unique_with_the_migration_constraint_name():
    uniques = {c.name: c for c in _table().constraints if isinstance(c, UniqueConstraint)}
    assert [c.name for c in uniques["learning_documents_task_id_key"].columns] == ["task_id"]


def test_check_constraints_keep_the_migration_names():
    checks = {
        c.name: str(c.sqltext) for c in _table().constraints if isinstance(c, CheckConstraint)
    }
    status_check = checks["learning_documents_generation_status_check"]
    for status in ("'pending'", "'in_progress'", "'completed'", "'failed'"):
        assert status in status_check
    structure_check = checks["valid_content_structure"]
    assert "jsonb_typeof" in structure_check
    for number in range(1, 8):
        assert f"chapter{number}" in structure_check


def test_indexes_match_migration():
    indexes = {index.name: [c.name for c in index.columns] for index in _table().indexes}
    assert indexes == {
        "idx_learning_documents_task_id": ["task_id"],
        "idx_learning_documents_status": ["generation_status"],
        "idx_learning_documents_celery_task": ["celery_task_id"],
    }


def test_constants():
    assert LearningDocument.STATUSES == ("pending", "in_progress", "completed", "failed")
    assert LearningDocument.CHAPTER_KEYS == tuple(f"chapter{n}" for n in range(1, 8))


def test_can_be_built_with_required_fields_only():
    task_id = uuid.uuid4()
    content = {key: {"title": key} for key in LearningDocument.CHAPTER_KEYS}
    document = LearningDocument(task_id=task_id, content=content)
    assert document.task_id == task_id
    assert document.content == content
    assert document.generation_error is None
    assert document.celery_task_id is None


def test_task_and_learning_document_are_linked_one_to_one():
    configure_mappers()
    task = Task(project_id=uuid.uuid4(), task_number=1, title="첫 번째 태스크")
    document = LearningDocument(task=task, content={})
    assert document.task is task
    assert task.learning_document is document


def test_deleting_task_is_left_to_database_cascade():
    relationship = Task.__mapper__.relationships["learning_document"]
    assert relationship.uselist is False
    assert relationship.passive_deletes is True
    assert relationship.back_populates == "task"


def test_repr_shows_id_task_and_status():
    task_id = uuid.uuid4()
    text = repr(LearningDocument(task_id=task_id, content={}, generation_status="completed"))
    assert str(task_id) in text and "completed" in text
