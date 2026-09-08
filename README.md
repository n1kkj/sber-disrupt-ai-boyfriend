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
GEMINI_PROXY_URL=http://user:password@proxy-host:port
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_WEBHOOK_SECRET=random-secret
TELEGRAM_MODE=webhook
TELEGRAM_POLLING_TIMEOUT=25
TELEGRAM_PROXY_URL=http://user:password@proxy-host:port
PLATFORM_URL=http://localhost:3000
REDIS_URL=redis://redis:6379/0
REDIS_TASK_STATE_TTL_SECONDS=86400
CELERY_DEFAULT_QUEUE=messages
CELERY_MAX_RETRIES=3
CELERY_RETRY_BACKOFF_SECONDS=5
CELERY_RETRY_BACKOFF_MAX_SECONDS=300
CELERY_TASK_TIME_LIMIT_SECONDS=180
```

Для локального запуска без HTTPS укажите `TELEGRAM_MODE=polling`. Для production с HTTPS используйте `TELEGRAM_MODE=webhook`.

Для синхронизации аккаунтов сайт вызывает `POST /api/v1/auth/telegram/link` с Bearer-токеном и отправляет пользователя по полученной ссылке в Telegram. Telegram-first пользователь нажимает кнопку `Подключиться к платформе`, открывает ссылку, входит на сайт и вызывает `POST /api/v1/auth/telegram/claim` с токеном из query-параметра `telegram_link`.

Если Telegram или Gemini недоступны напрямую, задайте соответствующий proxy URL. Формат: `http://user:password@host:port`. Для Telegram прокси используется всеми запросами `requests`, для Gemini -- `httpx`-клиентом LangChain.

Запуск:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

Сообщение отправляется в Celery и сразу возвращает `202 Accepted`. Ответ
worker сохраняет в общую историю. Для повторяемого запроса передавайте
`X-Idempotency-Key`. Для отложенного сообщения передавайте в JSON
`scheduled_at` в будущем, например `2026-09-08T18:30:00+03:00`.

Основные маршруты: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`,
`GET /api/v1/auth/me`, `GET /api/v1/boyfriends`, `POST /api/v1/chats`,
`POST /api/v1/chats/{chat_id}/messages`,
`POST /api/v1/chats/{chat_id}/messages/{message_id}/cancel`,
`POST /api/v1/telegram/webhook`.

Фоновые процессы: `app` обслуживает API, `worker` обрабатывает сообщения,
`beat` зарезервирован для будущих регулярных задач, Redis хранит broker,
result backend и состояние отменяемых message tasks.

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
