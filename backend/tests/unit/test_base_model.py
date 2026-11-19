import uuid

from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def test_base_is_declarative_base():
    assert issubclass(Base, DeclarativeBase)


def test_base_metadata_has_naming_convention():
    convention = Base.metadata.naming_convention
    assert {"ix", "uq", "ck", "fk", "pk"} <= set(convention)


def test_mixins_provide_standard_columns():
    class Sample(UUIDPrimaryKeyMixin, TimestampMixin, Base):
        __tablename__ = "sample_for_base_test"
        name: Mapped[str] = mapped_column()

    table: Table = Sample.__table__  # type: ignore[assignment]
    assert {"id", "created_at", "updated_at", "name"} == set(table.columns.keys())
    assert table.c.id.primary_key
    assert isinstance(Sample(id=uuid.uuid4(), name="x").id, uuid.UUID)
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None
