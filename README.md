# Добавление пакетов

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

## Production

Выбрать сервер приложений (WEB/CGI)

Unicorn

```bash
python3 ./src/app.py
```




