from app.ddl import sanitize_identifier, unique_identifiers
def test_sanitize_basic():
    assert sanitize_identifier("client_FIO", "x") == "client_fio"
def test_sanitize_special_chars():
    assert sanitize_identifier("a b!c", "x") == "a_b_c"

def test_sanitize_non_ascii_uses_fallback():
    # Кириллица не входит в [a-zA-Z0-9_] -> имя схлопывается в fallback.
    assert sanitize_identifier("Доход, руб.", "col_1") == "col_1"

def test_sanitize_leading_digit():
    assert sanitize_identifier("1col", "x").startswith("col_")

def test_sanitize_empty_uses_fallback():
    assert sanitize_identifier("!!!", "fallback") == "fallback"

def test_unique_identifiers_dedup():
    assert unique_identifiers(["A", "a", "b"]) == ["a", "a_1", "b"]