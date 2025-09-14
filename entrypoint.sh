#!/bin/sh
set -e

echo "Aguardando banco de dados..."
until pg_isready -d "$DATABASE_URL"; do
  sleep 2
done

echo "Rodando migrations..."
alembic upgrade head

echo "Iniciando aplicação..."
exec gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}
