"""Сквозные тесты эндпоинта на реальном PostgreSQL
Требуют доступной БД (доступы — из переменных окружения, см. README)
"""
import io
import psycopg2
import pytest
from fastapi.testclient import TestClient
from app.db import _dsn
from app.main import app


def _db_available() -> bool:
    try:
        psycopg2.connect(_dsn()).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL недоступна")

client = TestClient(app)




def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_upload_csv_creates_table_with_correct_schema():
    csv_bytes = (
        "client_id;client_FIO;client_income\n"
        "cl_001;Иванов;85000.50\n"
        "cl_002;Петров;120000\n"
        "cl_003;Сидорова;95500.75\n"
        "cl_004;Кузнецов;73000\n"
        "cl_005;Смирнова;110250.20\n"
    ).encode("utf-8")

    resp = client.post("/upload", files={"file": ("clients.csv", io.BytesIO(csv_bytes), "text/csv")})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["rows_inserted"] == 5
    schema = {col["name"]: col["type"] for col in body["columns"]}
    assert schema["client_id"].startswith("varchar")
    assert schema["client_fio"].startswith("varchar")
    assert schema["client_income"] == "numeric"

    conn = psycopg2.connect(_dsn())
    with conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM clients")
        assert cur.fetchone()[0] == 5
        cur.execute("SELECT client_income FROM clients WHERE client_id = 'cl_001'")
        assert float(cur.fetchone()[0]) == 85000.50
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'clients' AND column_name = 'client_income'
        """)
        assert cur.fetchone()[0] == "numeric"
    conn.close()

def test_upload_xlsx_infers_multiple_types():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["id", "name", "amount", "active", "dt"])
    ws.append([1, "Alpha", 10.5, True, "2023-01-15"])
    ws.append([2, "Beta", 20, False, "2023-02-20"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = client.post(
        "/upload",
        files={"file": ("t.xlsx", buf,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200, resp.text
    schema = {col["name"]: col["type"] for col in resp.json()["columns"]}
    assert schema == {"id": "bigint", "name": "varchar(255)",
                      "amount": "numeric", "active": "boolean", "dt": "date"}

def test_upload_rejects_unsupported_extension():
    resp = client.post("/upload", files={"file": ("data.txt", io.BytesIO(b"a;b\n1;2\n"), "text/plain")})
    assert resp.status_code == 400