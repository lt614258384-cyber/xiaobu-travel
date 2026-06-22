# ── 小布的旅行 Dockerfile ──
# Railway-compatible production image

FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/uploads data/generated data/features

# Railway sets PORT=8080
EXPOSE 8080

# Run migrations then start the server
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
