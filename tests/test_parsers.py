import pytest
from app.parsers import ParseError, parse_csv, parse_file

def test_parse_csv_semicolon():
    content = "a;b\n1;x\n2;y\n".encode("utf-8")
    headers, rows = parse_csv(content)
    assert headers == ["a", "b"]
    assert rows == [["1", "x"], ["2", "y"]]

def test_parse_csv_comma():
    content = "a,b\n1,x\n".encode("utf-8")
    headers, rows = parse_csv(content)
    assert headers == ["a", "b"]
    assert rows == [["1", "x"]]

def test_bom_is_stripped():
    content = "﻿a;b\n1;2\n".encode("utf-8")
    headers, _ = parse_csv(content)
    assert headers[0] == "a"

def test_short_rows_padded():
    content = "a;b;c\n1;2\n".encode("utf-8")
    _, rows = parse_csv(content)
    assert rows == [["1", "2", ""]]

def test_duplicate_headers_rejected():
    with pytest.raises(ParseError):
        parse_csv("a;a\n1;2\n".encode("utf-8"))

def test_empty_header_rejected():
    with pytest.raises(ParseError):
        parse_csv("a;;c\n1;2;3\n".encode("utf-8"))

def test_unsupported_extension():
    with pytest.raises(ParseError):
        parse_file("data.txt", b"a;b\n1;2\n")