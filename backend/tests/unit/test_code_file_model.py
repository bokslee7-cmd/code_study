import uuid

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers
from src.models import CodeFile, UploadedCode
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

SUPPORTED_EXTENSIONS = (
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".java",
    ".cpp",
    ".c",
    ".txt",
    ".md",
)


def _table() -> Table:
    table = CodeFile.__table__
    assert isinstance(table, Table)
    return table


def test_code_file_is_registered_on_base_metadata():
    assert issubclass(CodeFile, Base)
    assert issubclass(CodeFile, UUIDPrimaryKeyMixin)
    assert Base.metadata.tables["code_files"] is _table()


def test_table_has_no_updated_at_so_timestamp_mixin_is_not_used():
    assert not issubclass(CodeFile, TimestampMixin)


def test_columns_match_migration_schema():
    assert set(_table().columns.keys()) == {
        "id",
        "uploaded_code_id",
        "file_name",
        "file_path",
        "file_extension",
        "file_size_bytes",
        "storage_path",
        "mime_type",
        "created_at",
    }


def test_column_types():
    columns = _table().c
    assert isinstance(columns.id.type, UUID)
    assert isinstance(columns.uploaded_code_id.type, UUID)
    assert isinstance(columns.file_name.type, String) and columns.file_name.type.length == 255
    assert isinstance(columns.file_path.type, Text)
    assert isinstance(columns.file_extension.type, String)
    assert columns.file_extension.type.length == 20
    assert isinstance(columns.file_size_bytes.type, Integer)
    assert isinstance(columns.storage_path.type, Text)
    assert isinstance(columns.mime_type.type, String) and columns.mime_type.type.length == 100
    assert isinstance(columns.created_at.type, DateTime) and columns.created_at.type.timezone


def test_nullability():
    columns = _table().c
    assert not columns.uploaded_code_id.nullable
    assert not columns.file_name.nullable
    assert not columns.storage_path.nullable
    for name in ("file_path", "file_extension", "file_size_bytes", "mime_type"):
        assert columns[name].nullable, name


def test_created_at_is_filled_by_the_database():
    assert _table().c.created_at.server_default is not None


def test_uploaded_code_id_references_uploaded_code_with_cascade_delete():
    foreign_keys = list(_table().c.uploaded_code_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "uploaded_code.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_supported_extension_check_keeps_the_migration_name():
    checks = {
        c.name: str(c.sqltext) for c in _table().constraints if isinstance(c, CheckConstraint)
    }
    extension_check = checks["supported_extension"]
    for extension in SUPPORTED_EXTENSIONS:
        assert f"'{extension}'" in extension_check, extension


def test_uploaded_code_id_index_matches_migration():
    indexes = {index.name: index for index in _table().indexes}
    assert [c.name for c in indexes["idx_code_files_uploaded_code_id"].columns] == [
        "uploaded_code_id"
    ]


def test_can_be_built_with_required_fields_only():
    uploaded_code_id = uuid.uuid4()
    code_file = CodeFile(
        uploaded_code_id=uploaded_code_id, file_name="main.py", storage_path="uploads/a/main.py"
    )
    assert code_file.uploaded_code_id == uploaded_code_id
    assert code_file.file_name == "main.py"
    assert code_file.storage_path == "uploads/a/main.py"
    assert code_file.file_path is None
    assert code_file.file_extension is None
    assert code_file.file_size_bytes is None
    assert code_file.mime_type is None


def test_supported_extensions_constant():
    assert CodeFile.SUPPORTED_EXTENSIONS == SUPPORTED_EXTENSIONS


def test_uploaded_code_and_code_files_are_linked_both_ways():
    configure_mappers()
    uploaded = UploadedCode(task_id=uuid.uuid4())
    code_file = CodeFile(file_name="a.py", storage_path="p", uploaded_code=uploaded)
    assert code_file.uploaded_code is uploaded
    assert uploaded.code_files == [code_file]


def test_deleting_uploaded_code_is_left_to_database_cascade():
    relationship = UploadedCode.__mapper__.relationships["code_files"]
    assert relationship.passive_deletes is True
    assert relationship.back_populates == "uploaded_code"


def test_repr_shows_id_name_and_extension():
    text = repr(CodeFile(file_name="main.py", storage_path="p", file_extension=".py"))
    assert "main.py" in text and ".py" in text
