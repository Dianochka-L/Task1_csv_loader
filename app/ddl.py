"""Ручная генерация для PostgreSQL
SQL собирается вручную из выведенной схемы: идентификаторы экранируются двойными
кавычками (синтаксис PostgreSQL), значения подставляются параметрами psycopg2
через плейсхолдер `%s`. Имена столбцов предварительно нормализуются до набора символов
"""
from __future__ import annotations
import re
from typing import List
from .type_inference import ColumnType

_IDENT_RE = re.compile(r"[^0-9a-zA-Z_]+")
# белый список
_ALLOWED_TYPES = {"bigint", "numeric", "boolean", "date", "timestamp"}

def sanitize_identifier(name: str, fallback: str) -> str:
    """Привести имя к безопасному SQL-идентификатору в нижнем регистре."""
    cleaned = _IDENT_RE.sub("_", name.strip().lower()).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned[:63] # ограничение на длину идентификатора

def unique_identifiers(names: List[str]) -> List[str]:
    result: List[str] = []
    seen: dict[str, int] = {}
    for i, name in enumerate(names):
        ident = sanitize_identifier(name, fallback=f"col_{i + 1}")
        if ident in seen:
            seen[ident] += 1
            ident = f"{ident}_{seen[ident]}"
        else:
            seen[ident] = 0
        result.append(ident)
    return result

def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def _validate_type(pg_type: str) -> None:
    base = pg_type.split("(")[0]
    if base not in _ALLOWED_TYPES and base != "varchar":
        raise ValueError(f"Недопустимый тип столбца: {pg_type}")

def build_drop_table(table: str) -> str:
    return f"DROP TABLE IF EXISTS {quote_ident(table)}"

def build_create_table(table: str, columns: List[str], types: List[ColumnType]) -> str:
    """Собрать здесь инструкцию CREATE TABLE из нормализованных имён и проверенных типов"""
    defs = []
    for col, col_type in zip(columns, types):
        _validate_type(col_type.pg_type)
        defs.append(f"{quote_ident(col)} {col_type.pg_type}")
    return f"CREATE TABLE {quote_ident(table)} ({', '.join(defs)})"

def build_insert(table: str, columns: List[str], placeholder: str = "%s") -> str:
    """Собрать параметризованный INSERT с плейсхолдером psycopg2 (`%s`)"""
    cols = ", ".join(quote_ident(c) for c in columns)
    vals = ", ".join([placeholder] * len(columns))
    return f"INSERT INTO {quote_ident(table)} ({cols}) VALUES ({vals})"