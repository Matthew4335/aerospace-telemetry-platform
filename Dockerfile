
FROM python:3.11-slim

# Python environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Application working directory
WORKDIR /app

# PostgreSQL client library for psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

RUN python -m pip install --no-cache-dir \
    -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY etl/ ./etl/
COPY ml/ ./ml/

# FastAPI HTTP port
EXPOSE 8000

# Start the API
CMD ["python", "-m", "uvicorn", "api.main:app", \
    "--host", "0.0.0.0", "--port", "8000"]
