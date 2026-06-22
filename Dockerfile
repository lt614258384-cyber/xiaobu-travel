FROM python:3.13-slim

WORKDIR /app

# Copy everything first to bust cache when code changes
COPY . .

# Install dependencies (always runs because COPY . above changes on every code push)
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p data/uploads data/generated data/features

EXPOSE 8080

CMD ["sh", "-c", "echo '=== Checking imports ===' && python -c 'import psycopg; print(\"psycopg version:\", psycopg.__version__)' && python -c 'from app import app; print(\"App import OK\")' && echo '=== Starting ===' && python -m alembic upgrade head 2>&1 && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
