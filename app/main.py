"""FastAPI-приложение"""
from __future__ import annotations
from fastapi import FastAPI, File, HTTPException, UploadFile
from .db import load_table
from .ddl import sanitize_identifier
from .parsers import ParseError, parse_file
# Тут я описываю заголовок и описание
app = FastAPI(
    title="Тестовое 1",
    description="Принимает .csv/.xlsx, создаёт таблицу в PostgreSQL по структуре файла и заполняет её",
    version="1.0.0",
)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 МБ максимум

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """Загрузить таблицу из файла в БД... формат ответа
    - table_name по умолчанию берётся из имени файла
    - структура и типы столбцов выводятся автоматически
    - в ответе — имя таблицы, схема и число вставленных строк
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Пустой файл")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс 25 МБ)")
    try:
        headers, rows = parse_file(file.filename or "", content)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_name = (file.filename or "uploaded_table").rsplit(".", 1)[0]
    table = sanitize_identifier(base_name, fallback="uploaded_table")
    try:
        summary = load_table(table, headers, rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # ошибки БД
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки в БД: {exc}") from exc

    return {"status": "ok", **summary}