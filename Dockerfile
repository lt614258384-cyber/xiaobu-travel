FROM python:3.13-slim

WORKDIR /app

# Copy everything first to bust cache when code changes
COPY . .

# Install dependencies (always runs because COPY . above changes on every code push)
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p data/uploads data/generated data/features

EXPOSE 8080

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
