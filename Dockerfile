# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn psycopg2-binary whitenoise dj-database-url

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Run migrations and start server
CMD python manage.py migrate && \
    gunicorn assessment_v3.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300 --access-logfile - --error-logfile -
