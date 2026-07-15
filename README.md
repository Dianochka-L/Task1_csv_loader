# Тестовое задание «Риск-технолог»

Сервис на FastAPI и PostgreSQL (мне было так удобнее, есть готовый браузерный интерфейс). Принимает по HTTP файл .csv или .xlsx, автоматически определяет структуру таблицы (имена и типы столбцов), создаёт таблицу в реляционной БД и заполняет её данными из файла.

И база, и сервис поднимаются контейнерами Docker — ничего локально ставить
не нужно, PostgreSQL работает в контейнере. Запуск одной командой:

```bash
docker compose up --build
```

По условию задачи готовые методы использовать нельзя (что было не очень удобно :))... разбор файла, вывод типов,
генерация DDL и вставка реализованы самостоятельно.

## Как работает

```
файл > parsers.py > type_inference.py > ddl.py > db.py > PostgreSQL
      (заголовки,   (тип каждого        (CREATE TABLE     (psycopg2,
        строки)       столбца)           + INSERT,         одна транзакция:
                                        вручную)         DROP/CREATE/INSERT)
```

1. **parsers.py** — читает .csv (с авто-определением разделителя ; , \t |) или .xlsx (openpyxl), возвращает заголовки и строки
  Проверяет, что таблица корректна... непустые уникальные заголовки, строки не
   шире заголовка
2. **type_inference.py** — для каждого столбца перебирает все непустые значения
  и подбирает самый узкий подходящий тип:
   bigint > numeric > boolean > date > timestamp > varchar(n)
3. **ddl.py** — нормализует имена в SQL-идентификаторы, собирает ещё
  CREATE TABLE и INSERT. Идентификаторы и значения экранируются через psycopg2.sql — защита от SQL-инъекций
4. **db.py** — выполняет DROP IF EXISTS > CREATE > INSERT одной транзакцией... при ошибке — полный откат). Вставка батчами



## Запуск Docker

```bash
docker compose up --build
```

Поднимутся два контейнера: db (PostgreSQL 16) и api (сервис). Сервис — на
[http://localhost:8000](http://localhost:8000), интерактивная документация — [http://localhost:8000/docs](http://localhost:8000/docs). Данные БД хранятся
в томе pgdata

### Пример запроса

```bash
curl -F "file=@sample_data/clients.csv" http://localhost:8000/upload
```

Ответ:

```json
{
  "status": "ok",
  "table": "clients",
  "columns": [
    {"name": "client_id",     "type": "varchar(255)"},
    {"name": "client_fio",    "type": "varchar(255)"},
    {"name": "client_income", "type": "numeric"}
  ],
  "rows_inserted": 5
}
```

Таблица с тремя столбцами (client_id varchar, client_FIO varchar, client_income numeric) и записями из файла. Проверить содержимое БД:

```bash
docker compose exec db psql -U loader -d loader -c "SELECT * FROM clients;"
```



## Эндпоинты


| Метод | Путь    | Описание                                    |
| ----- | ------- | ------------------------------------------- |
| GET   | /health | Проверка доступности сервиса                |
| POST  | /upload | Загрузка файла .csv/.xlsx, создание таблицы |


Имя таблицы берётся из имени файла

## Тесты

Модульные тесты БД не требуют:

```bash
pip install -r requirements.txt
pytest tests/test_type_inference.py tests/test_parsers.py tests/test_ddl.py -q
```

Сквозные тесты эндпоинта работают с реальным PostgreSQL... можно поднять БД
контейнером и запустите весь набор:

```bash
docker compose up -d db # только контейнер с PostgreSQL
pip install -r requirements.txt
pytest -q # test_api_integration.py подключится к БД
```

Без запущенной БД интеграционные тесты автоматически пропускаются.

## Локальный запуск без Docker

```bash
pip install -r requirements.txt
cp .env.example .env # поправить доступы к своей БД
export $(cat .env | xargs)
uvicorn app.main:app --reload
```

Пример оформления файла .env для :

```DB_HOST=localhost
DB_PORT=5432
DB_NAME=loader
DB_USER=loader
DB_PASSWORD=loader
```

