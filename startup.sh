#!/bin/bash
set -e

alembic upgrade head
exec gunicorn main:app --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker
