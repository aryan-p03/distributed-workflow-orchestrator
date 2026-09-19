from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from backend.infrastructure.runtime import sync_database_schema


def test_sync_database_schema_creates_task_input_payload(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"

    sync_database_schema(database_url)

    columns = {
        column["name"] for column in inspect(create_engine(database_url)).get_columns("tasks")
    }
    assert "input_payload" in columns


def test_sync_database_schema_upgrades_existing_task_table(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY)"))

    sync_database_schema(database_url)

    columns = {column["name"] for column in inspect(engine).get_columns("tasks")}
    assert "input_payload" in columns
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO tasks (id) VALUES (1)"))
        payload = conn.execute(text("SELECT input_payload FROM tasks WHERE id = 1")).scalar_one()
    assert payload == "{}"
