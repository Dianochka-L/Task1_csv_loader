"""Это для работы с PostgreSQL...
Таблица создаётся вручную по выведенной из файла схеме (см. ddl.py, type_inference.py)
"""
from __future__ import annotations
import os
import time
from contextlib import contextmanager
from typing import List
import psycopg2
from psycopg2.extras import execute_batch
from .ddl import build_create_table, build_drop_table, build_insert, unique_identifiers
from .type_inference import ColumnType, infer_schema

# Плейсхолдер параметров у psycopg2
PLACEHOLDER = "%s"

def _dsn() -> str:
    """DSN берётся из переменных окружения"""
    return (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'loader')} "
        f"user={os.getenv('DB_USER', 'loader')} "
        f"password={os.getenv('DB_PASSWORD', 'loader')}"
    )

def connect(retries: int = 10, delay: float = 1.5):
    """Функция для подключения к PostgreSQL с несколькими попытками..
    Ретраи нужны при старте в Docker, потому что у нас сервис может подняться раньше, чем БД
    успеет принять соединения
    """
    last_error = None
    for _ in range(retries):
        try:
            return psycopg2.connect(_dsn())
        except psycopg2.OperationalError as exc:
            last_error = exc
            time.sleep(delay)
    raise last_error

@contextmanager
def get_connection():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()

def load_table(table: str, headers: List[str], rows: List[List[str]]) -> dict:
    """Создать таблицу по структуре файла и заполнить её данными
    Возвращает сводку, где есть имя таблицы, схема столбцов и число вставленных строк
    При ошибке выполняется полный откат
    """
    columns = unique_identifiers(headers)
    types: List[ColumnType] = infer_schema(headers, rows)
    converted = [
        [col_type.to_value(row[i]) for i, col_type in enumerate(types)]
        for row in rows
    ]

    with get_connection() as conn:
        with conn, conn.cursor() as cur:
            cur.execute(build_drop_table(table))
            cur.execute(build_create_table(table, columns, types))
            if converted:
                execute_batch(cur, build_insert(table, columns, PLACEHOLDER),
                              converted, page_size=1000)

    return {
        "table": table,
        "columns": [{"name": c, "type": t.pg_type} for c, t in zip(columns, types)],
        "rows_inserted": len(converted),
    }