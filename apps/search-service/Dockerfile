# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/apps/search-service/src:/app/packages/shared/src:/app/packages/devkit/src

WORKDIR /app

RUN addgroup --system --gid 10001 appgroup \
    && adduser --system --uid 10001 --ingroup appgroup appuser

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY apps/search-service/src /app/apps/search-service/src
COPY apps/search-service/alembic /app/apps/search-service/alembic
COPY apps/search-service/alembic.ini /app/apps/search-service/alembic.ini
COPY packages/shared/src /app/packages/shared/src
COPY packages/devkit/src /app/packages/devkit/src

USER appuser
EXPOSE 8104
CMD ["python", "-m", "search_service"]
