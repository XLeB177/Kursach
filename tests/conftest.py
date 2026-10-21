"""Общие фикстуры тестов: отдельная тестовая база, чистая перед каждым тестом."""
from pathlib import Path

import pytest

from db.connection import execute_sql_file, get_connection

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = str(ROOT / "db" / "schema.sql")
SEED_PATH = str(ROOT / "db" / "seed.sql")

# Все таблицы проекта (для очистки перед каждым тестом)
TABLES = (
    "users", "categories", "products", "favorites", "cart_items",
    "orders", "order_items", "suppliers", "supplier_products",
)


@pytest.fixture(scope="session", autouse=True)
def _prepare_test_db():
    """Проверяет, что тесты идут на тестовой базе, и создаёт таблицы."""
    conn = get_connection(test=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            name = cur.fetchone()[0]
    finally:
        conn.close()
    if not name.endswith("_test"):
        # Защита: рабочую базу тесты трогать не должны
        pytest.exit(f"Тесты запущены не на тестовой базе: {name}", returncode=2)
    execute_sql_file(SCHEMA_PATH, test=True)


@pytest.fixture
def db():
    """Соединение с чистой тестовой базой (все таблицы пусты)."""
    conn = get_connection(test=True)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
    conn.commit()
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def seed_db(db):
    """Тестовая база с загруженными данными из seed.sql."""
    execute_sql_file(SEED_PATH, test=True)
    return db
