"""Транзакции для запросов приложения."""
from contextlib import contextmanager

from psycopg2.extras import RealDictCursor

from db.connection import get_connection


@contextmanager
def transaction():
    conn = get_connection()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
    finally:
        conn.close()
