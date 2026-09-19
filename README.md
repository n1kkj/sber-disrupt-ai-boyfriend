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
GEMINI_TRANSCRIPTION_MODEL=your-transcription-model
GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview
GEMINI_TTS_VOICE=Kore
GEMINI_TTS_RESPONSE_FORMAT=
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_BASE_URL=https://api.artemox.com/v1
GEMINI_NATIVE_BASE_URL=https://api.artemox.com
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
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
LOG_MAX_BYTES=10000000
LOG_BACKUP_COUNT=5
RATE_LIMIT_MAX_MESSAGES=20
RATE_LIMIT_WINDOW_SECONDS=60
```

Для локального запуска без HTTPS укажите `TELEGRAM_MODE=polling`. Для production с HTTPS используйте `TELEGRAM_MODE=webhook`.

Для синхронизации аккаунтов сайт вызывает `POST /api/v1/auth/telegram/link` с Bearer-токеном и отправляет пользователя по полученной ссылке в Telegram. Telegram-first пользователь нажимает кнопку `Подключиться к платформе`, открывает ссылку, входит на сайт и вызывает `POST /api/v1/auth/telegram/claim` с токеном из query-параметра `telegram_link`.

Если Telegram или Gemini недоступны напрямую, задайте соответствующий proxy URL. Формат: `http://user:password@host:port`. Для Telegram прокси используется всеми запросами `requests`, для Gemini -- `httpx`-клиентом LangChain.

Запуск:

```bash
docker compose up -d --build
```

Перед запуском API/worker/beat одноразовый сервис `migrate` выполняет `alembic upgrade head`. Сообщение отправляется в Celery и сразу возвращает `202 Accepted`. Ответ
worker сохраняет в общую историю. Для повторяемого запроса передавайте
`X-Idempotency-Key`. Для отложенного сообщения передавайте в JSON
`scheduled_at` в будущем, например `2026-09-08T18:30:00+03:00`.

Основные маршруты: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`,
`GET /api/v1/auth/me`, `GET /api/v1/boyfriends`, `POST /api/v1/chats`,
`POST /api/v1/chats/{chat_id}/messages`,
`POST /api/v1/chats/{chat_id}/messages/{message_id}/cancel`,
`GET /api/v1/memory/facts`, `DELETE /api/v1/memory/facts/{fact_id}`,
`POST /api/v1/chats/{chat_id}/media`,
`POST /api/v1/telegram/webhook`.

Фоновые процессы: `app` обслуживает API, `worker` обрабатывает сообщения и
медиа и память в очередях `messages`, `audio`, `image`, `video`, `tts`, `memory`, `proactive`.
`beat` запускает регулярный поиск кандидатов для проактивных сообщений, Redis хранит broker,
result backend и состояние отменяемых message tasks.

Для текста и media используется OpenAI-compatible LiteLLM gateway через
`GEMINI_BASE_URL`; ключ передаётся только backend worker-ам. Медиафайлы пока
сохраняются локально в `MEDIA_STORAGE_PATH`. В Telegram обычные ответы
отправляются текстом. Чтобы дополнительно получить голосовой ответ, добавьте
к сообщению команду `/audio`, например:

```text
Мне тревожно перед собеседованием, как успокоиться? /audio
```

Ограничения
размера и длительности задаются через `MEDIA_*`. Видео обрабатывается кадрами
с интервалом `MEDIA_VIDEO_FRAME_INTERVAL_SECONDS` и ограничением
`MEDIA_VIDEO_MAX_FRAMES`; для аудио и видео используется `ffprobe`/`ffmpeg`.
При локальном запуске установите `ffmpeg` в систему; Dockerfile устанавливает
его автоматически.

Для каждого пользователя используются отдельные чаты `web` и `telegram`.
При связывании аккаунтов оба чата создаются автоматически, а ответ Celery
доставляется только в тот канал, из которого пришло исходное сообщение.
Кнопка подключения в Telegram показывается только до связывания аккаунта.

Для входящих сообщений действует Redis rate limit: по умолчанию 20 сообщений
за 60 секунд на web-пользователя и Telegram-чат.

Логирование единое для API, Telegram и Celery: записи идут в консоль и в
`logs/app.log` с ротацией файла. В логах нет паролей, токенов и полного текста
сообщений.

RAG по истории пока намеренно простой: к последним сообщениям добавляются исторические сообщения с пересечением слов запроса и текста. Поверх него работает отдельная структурированная память о фактах, людях, эпизодах и событиях. `GET /api/v1/memory/facts` возвращает только активные факты текущего пользователя. `DELETE /api/v1/memory/facts/{fact_id}` логически открепляет факт от пользовательской памяти: retrieval его больше не использует, но запись и отдельное событие удаления остаются в БД для внутренней аналитики.

На текущем этапе **автоматическое забывание отключено**. Shadow memory-agent не получает в своей active JSON-схеме операции удаления/замены и не помечает старые факты `superseded` при противоречии с новым сообщением. Заготовки для model-driven deletion/conflict resolution сохранены в DTO/service-коде и явно помечены `RESERVED / DISABLED`, но не подключены к worker pipeline и не занимают prompt/output tokens. Единственный активный destructive path для фактов — явный пользовательский `DELETE /api/v1/memory/facts/{fact_id}`. `do_not_store_turn` остаётся отдельным write-gate для текущего сообщения и не удаляет уже сохранённые факты.

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
