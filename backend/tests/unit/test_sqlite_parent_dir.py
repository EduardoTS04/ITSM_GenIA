"""ensure_sqlite_parent_dir must follow DATABASE_URL, never a hardcoded /app path."""

from pathlib import Path

from app.infrastructure.database.connection import ensure_sqlite_parent_dir


def test_creates_parent_of_sqlite_file(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "itsm.db"
    ensure_sqlite_parent_dir("sqlite:///" + db_path.as_posix())
    assert db_path.parent.is_dir()
    assert not db_path.exists()


def test_memory_and_non_sqlite_urls_are_noops(tmp_path: Path) -> None:
    ensure_sqlite_parent_dir("sqlite:///:memory:")
    ensure_sqlite_parent_dir("postgresql://localhost/itsm")
    assert list(tmp_path.iterdir()) == []
