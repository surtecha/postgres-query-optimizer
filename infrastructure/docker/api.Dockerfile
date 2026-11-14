FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANGGRAPH_STRICT_MSGPACK=true
COPY pyproject.toml ./
COPY packages ./packages
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = true ]; then python -m pip install --no-cache-dir ".[dev]"; else python -m pip install --no-cache-dir .; fi
RUN useradd --create-home --uid 10001 optimizer
COPY datasets ./datasets
COPY infrastructure/migrations ./infrastructure/migrations
COPY alembic.ini ./
RUN mkdir -p /app/state /app/experiments/reports && chown -R optimizer:optimizer /app
USER optimizer
CMD ["uvicorn", "optimizer.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
