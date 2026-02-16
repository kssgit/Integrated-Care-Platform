# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/apps/facility-service/src:/app/packages/shared/src:/app/packages/devkit/src

WORKDIR /app

RUN addgroup --system --gid 10001 appgroup \
    && adduser --system --uid 10001 --ingroup appgroup appuser

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY apps/facility-service/src /app/apps/facility-service/src
COPY apps/facility-service/alembic /app/apps/facility-service/alembic
COPY apps/facility-service/alembic.ini /app/apps/facility-service/alembic.ini
COPY packages/shared/src /app/packages/shared/src
COPY packages/devkit/src /app/packages/devkit/src

USER appuser
EXPOSE 8103
CMD ["python", "-m", "facility_service"]
