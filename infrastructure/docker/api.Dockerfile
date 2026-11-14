FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANGGRAPH_STRICT_MSGPACK=true
COPY pyproject.toml ./
COPY packages ./packages
RUN python -m pip install --no-cache-dir . && useradd --create-home --uid 10001 optimizer
COPY datasets ./datasets
COPY infrastructure/migrations ./infrastructure/migrations
COPY alembic.ini ./
RUN mkdir -p /app/state /app/experiments/reports && chown -R optimizer:optimizer /app
USER optimizer
CMD ["uvicorn", "optimizer.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
