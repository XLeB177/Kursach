"""Создание таблиц и необязательная загрузка демонстрационных данных."""
from argparse import ArgumentParser
from pathlib import Path

from psycopg2 import Error

from db.connection import execute_sql_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Загрузить игры и поставщиков для демонстрации")
    args = parser.parse_args()
    try:
        execute_sql_file(ROOT / "db" / "schema.sql")
        if args.demo:
            execute_sql_file(ROOT / "db" / "seed.sql")
    except Error:
        parser.exit(1, "Не удалось настроить базу. Проверьте имя базы, реквизиты и права в PostgreSQL.\n")
    print("База данных подготовлена")


if __name__ == "__main__":
    main()
