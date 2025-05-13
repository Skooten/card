# Добавление пакетов


```sh
git clone git@github.com:Skooten/card.git

cd card
uv venv
. ./.venv/bin/activate
uv sync
```

## Установка пакетов

```
flask flask_cors sqlalchemy psycopg2
```

## Запуск

```sh
python3 ./src/app.py
```

## Deploy

Запуск базы

```bash
docker compose up
docker compose up -d
```

Экпорт

```
pg_dump ....
```

Импорт

```sh
# on docker host
psql -h 127.0.0.1 -p 5432 -U postgres_user -W postgres_db < db_dump_UTF8.sql
# on client host
psql -h 127.0.0.1 -p 5555 -U postgres_user -W postgres_db < db_dump_UTF8.sql
```

## Production

Выбрать сервер приложений (WEB/CGI)

Unicorn

```bash
python3 ./src/app.py
# open http://127.0.0.1:5000/
```



