#!/bin/sh
set -e

until psql "$DATABASE_URL" -c '\q'; do
  echo "Aguardando banco..."
  sleep 2
done

echo "Rodando migrations..."
alembic upgrade head

echo "Iniciando aplicação..."
exec gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}
