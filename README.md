### AI boyfriend MVP backend

Минимальный backend для MVP: регистрация, профили, персонажи, чаты, простая память, Gemini и Telegram webhook.

Переменные `.env`:

```env
DB_HOST=db
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASS=postgres
JWT_SECRET=replace-with-a-long-random-string
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_WEBHOOK_SECRET=random-secret
```

Запуск:

```bash
docker compose up -d --build
alembic upgrade head
```

Основные маршруты: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `GET /api/v1/boyfriends`, `POST /api/v1/chats`, `POST /api/v1/chats/{chat_id}/messages`, `POST /api/v1/telegram/webhook`.

RAG пока намеренно простой: к последним сообщениям добавляются до восьми исторических сообщений с пересечением слов запроса и текста. Это дешевый MVP-слой, который можно заменить на embeddings/pgvector после появления реальных диалогов.

---

Шаблон проекта:

__V 1.0__

----

This is free to use fastapi template from @n1kkj

I personally used it in many of my projects, including fully working sites, services in big micro-service structures, telegram bots and more!

It uses uvicorn and docker to run, the command for start and restart:

```
docker compose up -d --build --force-recreate
```

And to stop containers:
```
docker compose down
```

To generate and perform alembic migrations:

```
alembic revision --autogenerate -m "init"
alembic upgrade head
```

Contact me in telegram @n1kkj if you have any suggestions or questions

**Or**

Comment on [discussion page](https://github.com/n1kkj/fastapi-template/discussions/1)

----

## Lets create best fastapi apps together!
