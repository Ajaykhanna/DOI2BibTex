# DOI2BibTeX Deployment Guide

Complete guide for deploying DOI2BibTeX in various environments, from local development to production.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Production Deployment](#production-deployment)
- [Monitoring & Health Checks](#monitoring--health-checks)
- [Scaling & Performance](#scaling--performance)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start all services (API + Web UI)
docker-compose up -d

# Access services
# - Web UI: http://localhost:8501
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Option 2: Local Python Installation

```bash
# Install with all dependencies
pip install -e ".[all]"

# Run Web UI
streamlit run streamlit_app.py

# Run API Server
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Run CLI
doi2bibtex --help
```

---

## Deployment Options

### 1. Docker Compose (Easiest)
- **Best for**: Development, testing, small-scale production
- **Pros**: Simple setup, all services orchestrated, easy scaling
- **Cons**: Requires Docker installed

### 2. Docker Individual Services
- **Best for**: Microservice architectures, cloud deployments
- **Pros**: Flexible, can deploy services independently
- **Cons**: More complex orchestration

### 3. Native Python Installation
- **Best for**: Development, custom environments
- **Pros**: Direct access to code, easier debugging
- **Cons**: Manual dependency management

### 4. Cloud Platforms
- **Best for**: Production workloads
- **Platforms**: AWS, GCP, Azure, DigitalOcean, Heroku
- **Pros**: Scalable, managed infrastructure
- **Cons**: Platform-specific configuration

---

## Docker Deployment

### Prerequisites

```bash
# Install Docker and Docker Compose
docker --version  # Should be 20.10+
docker-compose --version  # Should be 1.29+
```

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                DOI2BibTeX Stack                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐      ┌──────────────┐       │
│  │   Web UI     │      │  REST API    │       │
│  │  (Streamlit) │      │  (FastAPI)   │       │
│  │  Port: 8501  │      │  Port: 8000  │       │
│  └──────┬───────┘      └──────┬───────┘       │
│         │                     │                │
│         └──────────┬──────────┘                │
│                    │                           │
│         ┌──────────▼──────────┐                │
│         │   SQLite Database   │                │
│         │  (or PostgreSQL)    │                │
│         └─────────────────────┘                │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Basic Docker Compose Deployment

#### 1. Clone Repository

```bash
git clone https://github.com/Ajaykhanna/DOI2BibTex.git
cd DOI2BibTex
```

#### 2. Configure Environment (Optional)

```bash
# Create .env file for custom configuration
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./data/doi2bibtex.db
LOG_LEVEL=INFO
ENABLE_PLUGINS=false
EOF
```

#### 3. Start Services

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

#### 4. Verify Deployment

```bash
# Test API health
curl http://localhost:8000/health

# Test Web UI
curl http://localhost:8501/_stcore/health

# View API documentation
open http://localhost:8000/docs  # or visit in browser
```

#### 5. Stop Services

```bash
# Stop services (preserves data)
docker-compose stop

# Stop and remove containers (preserves data in volumes)
docker-compose down

# Stop and remove everything including volumes (CAUTION: deletes data)
docker-compose down -v
```

### Individual Service Deployment

#### Deploy API Server Only

```bash
# Build API image
docker-compose build api

# Start API service only
docker-compose up -d api

# Access API
curl http://localhost:8000/health
```

#### Deploy Web UI Only

```bash
# Build Web image
docker-compose build web

# Start Web service only
docker-compose up -d web

# Access Web UI
open http://localhost:8501
```

#### Deploy CLI Container

```bash
# Build CLI image
docker build --target cli -t doi2bibtex:cli .

# Run CLI commands
docker run --rm doi2bibtex:cli --version
docker run --rm doi2bibtex:cli convert "10.1038/nature12373"

# Mount volumes for file I/O
docker run --rm -v $(pwd)/data:/data doi2bibtex:cli \
    batch /data/dois.txt --output /data/output.bib
```

### Advanced Docker Compose Configuration

#### Using PostgreSQL Instead of SQLite

Edit `docker-compose.yml` and uncomment the PostgreSQL service:

```yaml
# Uncomment these lines in docker-compose.yml
postgres:
  image: postgres:15-alpine
  container_name: doi2bibtex-postgres
  environment:
    - POSTGRES_USER=doi2bibtex
    - POSTGRES_PASSWORD=doi2bibtex_password
    - POSTGRES_DB=doi2bibtex
  volumes:
    - postgres_data:/var/lib/postgresql/data
  restart: unless-stopped
  networks:
    - doi2bibtex
```

Update environment variables:

```bash
# Update .env file
DATABASE_URL=postgresql://doi2bibtex:doi2bibtex_password@postgres:5432/doi2bibtex
```

#### Adding Redis Cache (Optional)

Uncomment Redis service in `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  container_name: doi2bibtex-redis
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  restart: unless-stopped
```

---

## Environment Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/doi2bibtex.db` | Database connection string |
| `DOI2BIBTEX_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DOI2BIBTEX_PLUGINS` | `false` | Enable plugin system (Phase 5) |
| `DOI2BIBTEX_CACHE_DIR` | `.cache` | Cache directory path |
| `DOI2BIBTEX_MAX_WORKERS` | `10` | Maximum concurrent workers |
| `DOI2BIBTEX_TIMEOUT` | `30` | Request timeout in seconds |
| `API_HOST` | `0.0.0.0` | API server bind address |
| `API_PORT` | `8000` | API server port |
| `WEB_PORT` | `8501` | Streamlit web UI port |

### Configuration Methods

#### 1. Environment File (.env)

```bash
# Create .env file in project root
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./data/doi2bibtex.db
DOI2BIBTEX_LOG_LEVEL=INFO
DOI2BIBTEX_MAX_WORKERS=20
DOI2BIBTEX_TIMEOUT=60
EOF

# Docker Compose automatically loads .env
docker-compose up -d
```

#### 2. Direct Environment Variables

```bash
# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/doi2bibtex
export DOI2BIBTEX_LOG_LEVEL=DEBUG

# Run services
docker-compose up -d
```

#### 3. Docker Compose Override

```bash
# Create docker-compose.override.yml
cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  api:
    environment:
      - DOI2BIBTEX_LOG_LEVEL=DEBUG
      - DOI2BIBTEX_MAX_WORKERS=20
EOF

# Overrides are automatically applied
docker-compose up -d
```

### Database Configuration

#### SQLite (Default)

```bash
# Advantages: Simple, no setup required, good for development
# Limitations: Single-file, limited concurrency

DATABASE_URL=sqlite:///./data/doi2bibtex.db
```

#### PostgreSQL (Recommended for Production)

```bash
# Advantages: High performance, excellent concurrency, production-ready
# Setup: Requires PostgreSQL server

DATABASE_URL=postgresql://username:password@localhost:5432/doi2bibtex
```

#### Connection String Format

```
# SQLite
sqlite:///path/to/database.db

# PostgreSQL
postgresql://user:password@host:port/database

# PostgreSQL with SSL
postgresql://user:password@host:port/database?sslmode=require
```

---

## Production Deployment

### System Requirements

#### Minimum Requirements
- **CPU**: 1 core
- **RAM**: 512 MB
- **Disk**: 1 GB
- **Network**: Internet access for DOI resolution

#### Recommended Production
- **CPU**: 2+ cores
- **RAM**: 2+ GB
- **Disk**: 10+ GB (for database growth)
- **Network**: Stable connection with low latency

### Production Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS/TLS encryption
- [ ] Set up proper logging and monitoring
- [ ] Configure automatic backups
- [ ] Set resource limits (CPU, memory)
- [ ] Use secrets management for credentials
- [ ] Enable health checks and auto-restart
- [ ] Set up reverse proxy (nginx/traefik)
- [ ] Configure firewall rules
- [ ] Implement rate limiting
- [ ] Set up log rotation
- [ ] Test disaster recovery procedures

### Production Docker Compose Example

```yaml
version: '3.8'

services:
  api:
    image: doi2bibtex:api
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - DATABASE_URL=postgresql://doi2bibtex:${DB_PASSWORD}@postgres:5432/doi2bibtex
      - DOI2BIBTEX_LOG_LEVEL=WARNING
    volumes:
      - /var/doi2bibtex/data:/app/data
      - /var/doi2bibtex/cache:/app/.cache
    networks:
      - doi2bibtex
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      - POSTGRES_USER=doi2bibtex
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=doi2bibtex
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - doi2bibtex
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U doi2bibtex"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - doi2bibtex
    depends_on:
      - api
      - web

networks:
  doi2bibtex:
    driver: bridge

volumes:
  postgres_data:
    driver: local
```

### Nginx Reverse Proxy Configuration

```nginx
# nginx.conf
upstream api_backend {
    server api:8000;
}

upstream web_backend {
    server web:8501;
}

server {
    listen 80;
    server_name doi2bibtex.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name doi2bibtex.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # API endpoint
    location /api/ {
        proxy_pass http://api_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Web UI
    location / {
        proxy_pass http://web_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### Cloud Platform Deployments

#### AWS Elastic Container Service (ECS)

```bash
# 1. Build and push image to ECR
aws ecr create-repository --repository-name doi2bibtex-api
docker tag doi2bibtex:api ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/doi2bibtex-api:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/doi2bibtex-api:latest

# 2. Create ECS task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 3. Create ECS service
aws ecs create-service --cluster doi2bibtex-cluster \
    --service-name doi2bibtex-api \
    --task-definition doi2bibtex-api:1 \
    --desired-count 2
```

#### Google Cloud Run

```bash
# Build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/${PROJECT_ID}/doi2bibtex-api
gcloud run deploy doi2bibtex-api \
    --image gcr.io/${PROJECT_ID}/doi2bibtex-api \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

#### DigitalOcean App Platform

```bash
# Use doctl CLI
doctl apps create --spec .do/app.yaml

# Or use web interface with docker-compose.yml
# App Platform automatically detects docker-compose
```

#### Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create doi2bibtex-app

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:mini

# Deploy using container registry
heroku container:push web --app doi2bibtex-app
heroku container:release web --app doi2bibtex-app
```

---

## Monitoring & Health Checks

### Health Check Endpoints

#### API Server
```bash
# Simple health check
curl http://localhost:8000/health

# Response
{
  "status": "healthy",
  "version": "3.0.0",
  "timestamp": "2025-11-19T12:00:00Z"
}
```

#### Web UI
```bash
# Streamlit health endpoint
curl http://localhost:8501/_stcore/health

# Response
{
  "status": "ok"
}
```

### Docker Health Checks

Health checks are pre-configured in docker-compose.yml:

```bash
# View health status
docker-compose ps

# Output shows health status
NAME                    STATUS
doi2bibtex-api          Up (healthy)
doi2bibtex-web          Up (healthy)
```

### Monitoring with Prometheus

```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
  networks:
    - doi2bibtex
```

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'doi2bibtex-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

### Log Management

#### Docker Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100 api

# Follow logs with timestamps
docker-compose logs -f -t api
```

#### Log Aggregation (ELK Stack)

```yaml
# Add Elasticsearch and Kibana
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
  ports:
    - "9200:9200"

kibana:
  image: docker.elastic.co/kibana/kibana:8.11.0
  ports:
    - "5601:5601"
  depends_on:
    - elasticsearch
```

---

## Scaling & Performance

### Horizontal Scaling

#### Scale API Servers

```bash
# Scale API service to 3 instances
docker-compose up -d --scale api=3

# Add load balancer
docker-compose up -d nginx
```

#### Load Balancer Configuration

```nginx
# nginx load balancing
upstream api_backend {
    least_conn;  # or ip_hash or round_robin
    server api_1:8000;
    server api_2:8000;
    server api_3:8000;
}
```

### Vertical Scaling

```yaml
# Increase resource limits in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

### Performance Optimization

#### 1. Enable Async Processing

```bash
# Install aiohttp for async support
pip install doi2bibtex[performance]

# Async is automatically used when available
```

#### 2. Database Optimization

```sql
-- Create indexes for faster queries
CREATE INDEX idx_doi ON entries(doi);
CREATE INDEX idx_source ON entries(source);
CREATE INDEX idx_created_at ON entries(created_at);
```

#### 3. Caching Strategy

```bash
# Use Redis for distributed caching
DATABASE_URL=postgresql://...
REDIS_URL=redis://redis:6379/0
```

#### 4. Connection Pooling

```python
# Automatically configured in database.py
# Max 10 connections per worker
pool_size = 10
max_overflow = 20
```

### Performance Benchmarks

```bash
# Install benchmarking tools
pip install locust

# Run load test
locust -f tests/locustfile.py --host=http://localhost:8000
```

---

## Troubleshooting

### Common Issues

#### Issue: Container Won't Start

```bash
# Check container logs
docker-compose logs api

# Common causes:
# 1. Port already in use
sudo lsof -i :8000  # Check what's using port 8000

# 2. Missing environment variables
docker-compose config  # Verify configuration

# 3. Permission issues with volumes
sudo chown -R 1000:1000 ./data ./cache
```

#### Issue: Database Connection Failed

```bash
# Check database container
docker-compose logs postgres

# Verify connection string
docker-compose exec api env | grep DATABASE_URL

# Test connection manually
docker-compose exec api python -c "from core.database import DOIDatabase; db = DOIDatabase(); print('Connected!')"
```

#### Issue: API Returns 500 Errors

```bash
# Enable debug logging
export DOI2BIBTEX_LOG_LEVEL=DEBUG
docker-compose up -d

# Check detailed logs
docker-compose logs -f api

# Test API endpoint directly
curl -v http://localhost:8000/api/v1/doi/10.1038/nature12373
```

#### Issue: Slow Performance

```bash
# Check resource usage
docker stats

# Check database size
docker-compose exec api du -sh /app/data/doi2bibtex.db

# Clear cache
docker-compose exec api rm -rf /app/.cache/*
docker-compose restart api
```

#### Issue: Out of Memory

```bash
# Increase memory limits
# Edit docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G

# Restart services
docker-compose up -d
```

### Debug Mode

```bash
# Run containers in foreground with debug output
docker-compose up

# Run specific service with shell access
docker-compose run --rm api /bin/bash

# Inside container, test manually
python -c "from core.converter import DOIConverter; c = DOIConverter(); print(c.convert('10.1038/nature12373'))"
```

### Health Check Failures

```bash
# Check health status
docker inspect doi2bibtex-api | grep -A 10 Health

# Manual health check
docker-compose exec api curl http://localhost:8000/health

# Adjust health check parameters in docker-compose.yml
healthcheck:
  interval: 60s  # Check every 60 seconds
  timeout: 30s   # Wait 30 seconds for response
  retries: 5     # Retry 5 times before marking unhealthy
  start_period: 60s  # Wait 60s before starting checks
```

---

## Security Best Practices

### 1. Container Security

```dockerfile
# Use non-root user (already configured)
USER doi2bibtex

# Read-only root filesystem (add to docker-compose.yml)
read_only: true
tmpfs:
  - /tmp
```

### 2. Network Security

```yaml
# Restrict network access
networks:
  doi2bibtex:
    internal: true  # No external access
```

### 3. Secrets Management

```bash
# Use Docker secrets instead of environment variables
echo "my_db_password" | docker secret create db_password -

# Reference in docker-compose.yml
services:
  api:
    secrets:
      - db_password
    environment:
      - DATABASE_PASSWORD_FILE=/run/secrets/db_password
```

### 4. SSL/TLS Configuration

```bash
# Generate self-signed certificate (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ./ssl/key.pem -out ./ssl/cert.pem

# Use Let's Encrypt for production
certbot certonly --standalone -d doi2bibtex.example.com
```

### 5. Regular Updates

```bash
# Update base images regularly
docker-compose pull
docker-compose up -d

# Update application
git pull
docker-compose build
docker-compose up -d
```

### 6. Access Control

```yaml
# Require authentication (add to API)
API_KEY=${API_KEY}
REQUIRE_AUTH=true

# Use API key in requests
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/doi/...
```

---

## Backup & Recovery

### Database Backup

#### SQLite Backup

```bash
# Backup SQLite database
docker-compose exec api sqlite3 /app/data/doi2bibtex.db ".backup /app/data/backup.db"

# Copy backup to host
docker cp doi2bibtex-api:/app/data/backup.db ./backups/doi2bibtex-$(date +%Y%m%d).db

# Automated daily backup
# Add to crontab
0 2 * * * cd /path/to/DOI2BibTex && docker-compose exec -T api sqlite3 /app/data/doi2bibtex.db ".backup /app/data/backup-$(date +\%Y\%m\%d).db"
```

#### PostgreSQL Backup

```bash
# Backup PostgreSQL database
docker-compose exec postgres pg_dump -U doi2bibtex doi2bibtex > backup.sql

# Restore PostgreSQL database
docker-compose exec -T postgres psql -U doi2bibtex doi2bibtex < backup.sql

# Automated backup
0 2 * * * cd /path/to/DOI2BibTex && docker-compose exec -T postgres pg_dump -U doi2bibtex doi2bibtex | gzip > ./backups/doi2bibtex-$(date +\%Y\%m\%d).sql.gz
```

### Disaster Recovery

```bash
# 1. Stop services
docker-compose down

# 2. Restore data volume
docker run --rm -v doi2bibtex_data:/data -v $(pwd)/backups:/backup alpine \
    sh -c "cd /data && tar xzf /backup/data-backup.tar.gz"

# 3. Restore database
docker-compose up -d postgres
docker-compose exec -T postgres psql -U doi2bibtex doi2bibtex < backup.sql

# 4. Start all services
docker-compose up -d
```

---

## Performance Tuning

### Database Optimization

```sql
-- PostgreSQL tuning (add to postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 128MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 8MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### API Optimization

```bash
# Increase Uvicorn workers
# Edit docker-compose.yml
command: ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Enable HTTP/2
command: ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--http", "h11"]
```

### Caching Strategy

```python
# Configure aggressive caching
CACHE_TTL=86400  # 24 hours
CACHE_MAX_SIZE=10000  # 10k entries
```

---

## Support & Resources

### Documentation
- **README**: `/README.md`
- **API Docs**: http://localhost:8000/docs (when running)
- **GitHub**: https://github.com/Ajaykhanna/DOI2BibTex

### Getting Help
- **Issues**: https://github.com/Ajaykhanna/DOI2BibTex/issues
- **Discussions**: https://github.com/Ajaykhanna/DOI2BibTex/discussions

### Community
- Star the repository if you find it useful
- Report bugs and request features via GitHub Issues
- Contribute improvements via Pull Requests

---

**Last Updated**: Phase 6 - November 2025
**Version**: 3.0.0
**Maintained by**: Ajay Khanna (akhanna2@ucmerced.edu)
