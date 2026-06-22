# ── 小布的旅行 Dockerfile ──
# Railway-compatible production image

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (none needed beyond slim image)
# psycopg 3 is pure Python, no libpq required

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories (Railway provides persistent volume at /data)
RUN mkdir -p data/uploads data/generated data/features

# Expose the port Railway assigns (default 8000)
EXPOSE 8000

# Run migrations then start the server
CMD ["sh", "-c", "python -m alembic upgrade head && python run.py"]
