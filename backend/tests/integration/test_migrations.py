"""Integration tests for the Alembic migrations.

These run the real migration scripts against throwaway SQLite files and compare
the result with the schema the ORM models describe. That comparison is what keeps
`alembic upgrade head` and Base.metadata from drifting apart.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.infrastructure.database.connection import Base

BACKEND_DIR = Path(__file__).resolve().parents[2]

# The columns the old run_migrations() helper used to add with ALTER TABLE.
LEGACY_ALTER_COLUMNS = [
    "respuesta_estructurada", "escalado_a_humano", "es_recurrente",
    "causa_raiz", "accion_preventiva",
]


def alembic_config(db_path: Path) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", "sqlite:///" + db_path.as_posix())
    return config


def describe(url: str) -> dict:
    """Table -> column/index/foreign-key description, for comparing two schemas."""
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        return {
            table: {
                "columns": sorted(
                    (c["name"], str(c["type"]), c["nullable"])
                    for c in inspector.get_columns(table)
                ),
                "indexes": sorted(
                    (i["name"], tuple(i["column_names"]), bool(i["unique"]))
                    for i in inspector.get_indexes(table)
                ),
                "primary_key": inspector.get_pk_constraint(table)["constrained_columns"],
                "foreign_keys": sorted(
                    (
                        tuple(fk["constrained_columns"]),
                        fk["referred_table"],
                        tuple(fk["referred_columns"]),
                        fk.get("options", {}).get("ondelete"),
                    )
                    for fk in inspector.get_foreign_keys(table)
                ),
            }
            # alembic_version is bookkeeping, not part of the application schema.
            for table in inspector.get_table_names() if table != "alembic_version"
        }
    finally:
        engine.dispose()


@pytest.fixture
def migrated_url(tmp_path: Path) -> str:
    """A fresh SQLite database at head."""
    db_path = tmp_path / "migrated.db"
    command.upgrade(alembic_config(db_path), "head")
    return "sqlite:///" + db_path.as_posix()


@pytest.fixture
def orm_url(tmp_path: Path) -> str:
    """A fresh SQLite database built straight from the ORM models."""
    db_path = tmp_path / "from_models.db"
    url = "sqlite:///" + db_path.as_posix()
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    return url


# ── upgrade head ───────────────────────────────────────────────────────────────

def test_upgrade_head_creates_the_whole_schema(migrated_url):
    assert set(describe(migrated_url)) == {"tickets", "comments", "agent_traces"}


def test_migrated_schema_matches_the_orm_models(migrated_url, orm_url):
    """`alembic upgrade head` and create_all() must agree, table for table."""
    assert describe(migrated_url) == describe(orm_url)


def test_tickets_keeps_the_columns_the_old_alter_loop_added(migrated_url):
    columns = {name for name, _, _ in describe(migrated_url)["tickets"]["columns"]}

    assert set(LEGACY_ALTER_COLUMNS) <= columns


def test_head_is_recorded_in_the_version_table(tmp_path: Path):
    db_path = tmp_path / "stamped.db"
    config = alembic_config(db_path)

    command.upgrade(config, "head")

    engine = create_engine("sqlite:///" + db_path.as_posix())
    with engine.connect() as connection:
        from sqlalchemy import text
        versions = [row[0] for row in connection.execute(text("select version_num from alembic_version"))]
    engine.dispose()
    assert versions == ["0002"]


# ── Adopting Alembic on databases that predate it ──────────────────────────────

def test_a_pre_alembic_database_can_be_stamped_then_upgraded(tmp_path: Path):
    """The documented path for a database holding only tickets and comments."""
    db_path = tmp_path / "legacy.db"
    config = alembic_config(db_path)
    # Build the legacy schema, then insert a row that must survive.
    command.upgrade(config, "0001")
    engine = create_engine("sqlite:///" + db_path.as_posix())
    from sqlalchemy import text
    with engine.begin() as connection:
        connection.execute(text(
            "insert into tickets (titulo, descripcion, tipo, categoria, prioridad)"
            " values ('VPN', 'no conecta', 'incidente', 'Red', 'P1')"
        ))
    engine.dispose()

    command.stamp(config, "0001")
    command.upgrade(config, "head")

    engine = create_engine("sqlite:///" + db_path.as_posix())
    with engine.connect() as connection:
        rows = [row[0] for row in connection.execute(text("select titulo from tickets"))]
    engine.dispose()
    assert rows == ["VPN"]
    assert "agent_traces" in describe("sqlite:///" + db_path.as_posix())


def test_stamp_head_leaves_an_up_to_date_database_untouched(tmp_path: Path):
    """Databases that already have every table are adopted with `stamp head`."""
    db_path = tmp_path / "current.db"
    url = "sqlite:///" + db_path.as_posix()
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    with engine.begin() as connection:
        connection.execute(text(
            "insert into tickets (titulo, descripcion, tipo, categoria, prioridad)"
            " values ('Teclado', 'sin respuesta', 'requerimiento', 'Hardware', 'P4')"
        ))
    engine.dispose()
    before = describe(url)

    command.stamp(alembic_config(db_path), "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        rows = [row[0] for row in connection.execute(text("select titulo from tickets"))]
    engine.dispose()
    assert rows == ["Teclado"]
    assert describe(url) == before


# ── downgrade ──────────────────────────────────────────────────────────────────

def test_downgrade_unwinds_to_an_empty_schema(tmp_path: Path):
    db_path = tmp_path / "roundtrip.db"
    config = alembic_config(db_path)

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    assert describe("sqlite:///" + db_path.as_posix()) == {}
