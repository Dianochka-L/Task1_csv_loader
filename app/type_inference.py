"""Вывод типов столбцов по значениям
Для каждого столбца перебираем все непустые значения и подбираем самый
"узкий" тип, которому удовлетворяют все значения
BIGINT -> NUMERIC -> BOOLEAN -> DATE -> TIMESTAMP -> VARCHAR
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, List, Optional

_INT_RE = re.compile(r"^[+-]?\d+$")
_BOOL_TRUE = {"true", "t", "yes", "y", "1"}
_BOOL_FALSE = {"false", "f", "no", "n", "0"}
_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")
_TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M")


@dataclass(frozen=True)
class ColumnType:
    pg_type: str
    convert: Callable[[str], object]

    def to_value(self, raw: str) -> Optional[object]:
        if raw is None or raw.strip() == "":
            return None
        return self.convert(raw.strip())

def _is_int(v: str) -> bool:
    return bool(_INT_RE.match(v))




def _is_numeric(v: str) -> bool:
    try:
        Decimal(v)
        return True
    except InvalidOperation:
        return False

def _is_bool(v: str) -> bool:
    return v.lower() in _BOOL_TRUE or v.lower() in _BOOL_FALSE

def _parse_bool(v: str) -> bool:
    return v.lower() in _BOOL_TRUE

def _match_formats(v: str, formats) -> bool:
    for fmt in formats:
        try:
            datetime.strptime(v, fmt)
            return True
        except ValueError:
            continue
    return False

def _parse_date(v: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Не удалось разобрать дату: {v!r}")

def _parse_ts(v: str) -> datetime:
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    raise ValueError(f"Не удалось разобрать дату-время: {v!r}")

def infer_column_type(values: List[str]) -> ColumnType:
    non_empty = [v.strip() for v in values if v is not None and v.strip() != ""]
    # Столбец без данных — считаем текстовым
    if not non_empty:
        return ColumnType("varchar", str)
    if all(_is_int(v) for v in non_empty):
        return ColumnType("bigint", int)

    if all(_is_numeric(v) for v in non_empty):
        return ColumnType("numeric", Decimal)

    if all(_is_bool(v) for v in non_empty):
        return ColumnType("boolean", _parse_bool)

    if all(_match_formats(v, _DATE_FORMATS) for v in non_empty):
        return ColumnType("date", _parse_date)

    if all(_match_formats(v, _TS_FORMATS) for v in non_empty):
        return ColumnType("timestamp", _parse_ts)
    max_len = max(len(v) for v in non_empty)
    length = max(255, ((max_len // 8) + 1) * 8)
    return ColumnType(f"varchar({length})", str)


def infer_schema(headers: List[str], rows: List[List[str]]) -> List[ColumnType]:
    columns: List[ColumnType] = []
    for idx in range(len(headers)):
        column_values = [row[idx] for row in rows]
        columns.append(infer_column_type(column_values))
    return columns