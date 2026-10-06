"""Подключение к PostgreSQL по параметрам из .env."""

from pathlib import Path

import psycopg2
from dotenv import load_dotenv
import os

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def get_connection_params(*, test: bool = False) -> dict:
    """Параметры подключения. test=True — база board_games_test."""
    db_name_key = "DB_TEST_NAME" if test else "DB_NAME"
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv(db_name_key, "board_games_test" if test else "board_games"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


def get_connection(*, test: bool = False):
    """Открыть соединение с рабочей или тестовой базой."""
    return psycopg2.connect(**get_connection_params(test=test))


if __name__ == "__main__":
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            print(cur.fetchone()[0])
    finally:
        conn.close()
