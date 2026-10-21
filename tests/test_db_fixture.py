"""Проверка фикстур тестовой базы и данных seed.sql."""
TABLES = (
    "users", "categories", "products", "favorites", "cart_items",
    "orders", "order_items", "suppliers", "supplier_products",
)


def _count(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]


def test_database_is_test(db):
    """Тесты работают на базе, имя которой заканчивается на _test."""
    with db.cursor() as cur:
        cur.execute("SELECT current_database()")
        assert cur.fetchone()[0].endswith("_test")


def test_tables_are_empty(db):
    """В начале теста все таблицы пусты."""
    for table in TABLES:
        assert _count(db, table) == 0, table


def test_insert_category(db):
    """Вставляем запись (следующий тест должен её не увидеть)."""
    with db.cursor() as cur:
        cur.execute("INSERT INTO categories (name) VALUES (%s)", ("Тест",))
    db.commit()
    assert _count(db, "categories") == 1


def test_clean_after_previous(db):
    """Запись из предыдущего теста удалена: каждый тест начинается с чистой базы."""
    assert _count(db, "categories") == 0


def test_seed_loaded(seed_db):
    """seed.sql загружается и даёт ожидаемое количество строк."""
    assert _count(seed_db, "categories") == 8
    assert _count(seed_db, "products") == 15
    assert _count(seed_db, "suppliers") == 3
    assert _count(seed_db, "supplier_products") == 16
    with seed_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM products WHERE quantity = 0")
        assert cur.fetchone()[0] == 1
