# Программа Учёта катриджей

Состав:

- Python Flask - Веб фреймворк
- ORM Alchemy
- PostgreSQL - База данных

Установка:

```sh
# клонируем репозиторий проекта
git clone git@github.com:Skooten/card.git

# переходим в папку с проектом
cd card

# Подключаем виртуальное окржуние
. ./.venv/bin/activate
# Обновляем пакеты
uv sync

# Запускаем docker контейнер с базой данной
docker compose up -d

# Запуск проекта
python3 ./src/app.py
# open http://127.0.0.1:5000/
```

## Импорт sql

```sh
# on docker host
psql -h 127.0.0.1 -p 5432 -U postgres_user -W postgres_db < db_dump_UTF8.sql
# on client host
psql -h 127.0.0.1 -p 5555 -U postgres_user -W postgres_db < db_dump_UTF8.sql
```
