FROM python:3.11-slim

# Evita cache e melhora performance
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONMALLOC=malloc \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# Cria usuário não-root
RUN adduser --disabled-password --gecos '' appuser

# Instala dependências mínimas do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copia dependências e instala pacotes
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip cache purge

# Copia a aplicação
COPY . .

USER appuser

EXPOSE 5000

# Healthcheck para monitoramento
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Usa Gunicorn com UvicornWorker para FastAPI
CMD ["gunicorn", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "1", \
     "--threads", "2", \
     "--worker-tmp-dir", "/dev/shm", \
     "--max-requests", "300", \
     "--max-requests-jitter", "50", \
     "--timeout", "30", \
     "--graceful-timeout", "20", \
     "--keep-alive", "5", \
     "--bind", "0.0.0.0:5000", \
     "main:app"]

