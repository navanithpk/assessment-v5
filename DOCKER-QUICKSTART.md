# Docker Quick Start Guide

## Local Development with Docker

### Prerequisites
- Docker Desktop installed (download from https://docs.docker.com/get-docker/)
- Git (for version control)

### Quick Start

1. **Build the Docker image:**
   ```bash
   docker build -t assessment-platform .
   ```

2. **Run locally with SQLite:**
   ```bash
   docker run -p 8080:8080 \
     -e SECRET_KEY="dev-secret-key-change-in-production" \
     -e DEBUG="True" \
     -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
     assessment-platform
   ```

3. **Access the application:**
   - Open browser to http://localhost:8080
   - Login or create accounts

### Run with Environment File

1. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Run with env file:**
   ```bash
   docker run -p 8080:8080 --env-file .env assessment-platform
   ```

### Docker Compose (Optional)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SECRET_KEY=dev-secret-key
      - DEBUG=True
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/assessment
    depends_on:
      - db
    volumes:
      - ./:/app
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn assessment_v3.wsgi:application --bind 0.0.0.0:8080 --reload"

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=assessment
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up
```

### Useful Docker Commands

```bash
# Build image
docker build -t assessment-platform .

# Run container
docker run -p 8080:8080 assessment-platform

# Run with shell access
docker run -it -p 8080:8080 assessment-platform /bin/bash

# View running containers
docker ps

# View logs
docker logs <container-id>

# Stop container
docker stop <container-id>

# Remove container
docker rm <container-id>

# Remove image
docker rmi assessment-platform

# Run Django commands in container
docker run assessment-platform python manage.py migrate
docker run assessment-platform python manage.py createsuperuser
docker run assessment-platform python manage.py collectstatic

# Interactive shell in running container
docker exec -it <container-id> /bin/bash
```

### Debugging

**Container won't start:**
```bash
# Check build logs
docker build -t assessment-platform . --progress=plain

# Run with shell to debug
docker run -it --entrypoint /bin/bash assessment-platform
```

**Port already in use:**
```bash
# Use different port
docker run -p 8000:8080 assessment-platform

# Or find and kill process on port 8080
# Windows: netstat -ano | findstr :8080
# Linux/Mac: lsof -ti:8080 | xargs kill
```

**Database connection issues:**
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL

# For Cloud SQL, ensure unix socket path is correct
# postgresql://USER:PASS@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
```

### Production Checklist

Before deploying to production:
- [ ] Set strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Use production database (PostgreSQL)
- [ ] Set up static file serving
- [ ] Configure Google OAuth credentials
- [ ] Test all critical paths
- [ ] Set up monitoring and logging

### Next Steps

1. **Local Development**: Use the Docker Compose setup above
2. **Production Deployment**: Follow DEPLOYMENT.md for Google Cloud Run
3. **Custom Domain**: Configure after Cloud Run deployment
