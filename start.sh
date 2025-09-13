#!/bin/bash

# Script de inicialização para produção

echo "🚀 Iniciando Gomech AI Service..."

# Verifica se as variáveis de ambiente necessárias estão definidas
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Erro: DATABASE_URL não definida"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Erro: OPENAI_API_KEY não definida"
    exit 1
fi

echo "✅ Variáveis de ambiente verificadas"

# Executa migrações do banco de dados
echo "🔄 Executando migrações do banco de dados..."
python -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrações executadas com sucesso"
else
    echo "❌ Erro ao executar migrações"
    exit 1
fi

# Inicia o servidor
echo "🌐 Iniciando servidor..."
exec gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --log-level info
