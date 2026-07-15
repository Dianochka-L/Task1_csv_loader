from decimal import Decimal

from app.type_inference import infer_column_type, infer_schema

def test_integer_column():
    assert infer_column_type(["1", "2", "3"]).pg_type == "bigint"

def test_numeric_column():
    col = infer_column_type(["85000.50", "120000", "95500.75"])
    assert col.pg_type == "numeric"
    assert col.to_value("85000.50") == Decimal("85000.50")

def test_varchar_when_mixed():
    assert infer_column_type(["cl_001", "cl_002"]).pg_type.startswith("varchar")

def test_boolean_column():
    assert infer_column_type(["true", "false", "1", "0"]).pg_type == "boolean"

def test_date_column():
    assert infer_column_type(["2023-03-04", "2023-03-05"]).pg_type == "date"

def test_empty_cells_are_null_and_ignored_for_type():
    col = infer_column_type(["1", "", "3"])
    assert col.pg_type == "bigint"
    assert col.to_value("") is None

def test_all_empty_defaults_to_varchar():
    assert infer_column_type(["", ""]).pg_type == "varchar"

def test_schema_matches_task_example():
    headers = ["client_id", "client_FIO", "client_income"]
    rows = [
        ["cl_001", "Иванов Иван", "85000.50"],
        ["cl_002", "Петров Пётр", "120000"],
    ]
    types = [c.pg_type for c in infer_schema(headers, rows)]
    assert types[0].startswith("varchar")
    assert types[1].startswith("varchar")
    assert types[2] == "numeric"