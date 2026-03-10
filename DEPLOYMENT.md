# NextGen AI Tutor - Deployment Guide

## Overview

This document provides comprehensive deployment instructions for the NextGen AI Tutor platform, covering development, staging, and production environments.

## Architecture

### System Components
1. **FastAPI Backend** - Main API server with WebSocket support
2. **PostgreSQL + TimescaleDB** - Primary database with time-series capabilities
3. **Redis** - Session management, caching, and message queue
4. **AI Model Server** - Separate service for AI model inference
5. **Worker** - Background task processing (Celery)
6. **Monitoring Stack** - Prometheus, Grafana, ELK (optional)

### Network Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│     Nginx       │────│   FastAPI API   │
│   (Production)  │    │   (Optional)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │                     │
                                 ▼                     ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   PostgreSQL    │    │      Redis      │
                        │  + TimescaleDB  │    │                 │
                        └─────────────────┘    └─────────────────┘
                                 │                     │
                                 ▼                     ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   AI Model      │    │     Worker      │
                        │     Server      │    │    (Celery)     │
                        └─────────────────┘    └─────────────────┘
```

## Prerequisites

### Development
- Docker & Docker Compose
- Python 3.11+
- Git

### Production
- Docker & Docker Compose (or Kubernetes)
- PostgreSQL 15+ with TimescaleDB extension
- Redis 7+
- Nginx (for load balancing)
- SSL certificates
- Domain name

## Quick Start (Development)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd nextgen-ai-tutor

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Start Services
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service status
docker-compose ps
```

### 3. Initialize Database
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create admin user (optional)
docker-compose exec api python -c "
from core.database import init_db
import asyncio
asyncio.run(init_db())
print('Database initialized')
"
```

### 4. Access Services
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redis Insight**: http://localhost:8001
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Production Deployment

### 1. Infrastructure Setup

#### Option A: Docker Compose (Single Server)
```bash
# Create production directory
mkdir -p /opt/ai-tutor
cd /opt/ai-tutor

# Clone repository
git clone <repository-url> .

# Create production environment file
cp .env.example .env.production
nano .env.production  # Update all production values

# Create data directories
mkdir -p data/postgres data/redis data/logs data/uploads

# Set permissions
chown -R 1000:1000 data/

# Start services
docker-compose -f docker-compose.yml --env-file .env.production up -d
```

#### Option B: Kubernetes (Multi-server)
```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configs/
kubectl apply -f kubernetes/secrets/
kubectl apply -f kubernetes/services/
kubectl apply -f kubernetes/deployments/
```

### 2. Database Setup

#### PostgreSQL with TimescaleDB
```bash
# Install TimescaleDB extension
docker-compose exec postgres psql -U postgres -d ai_tutor -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Create read replica (for production)
# Add to docker-compose.yml:
# postgres-replica:
#   image: timescale/timescaledb:latest-pg15
#   command: postgres -c hot_standby=on
#   volumes:
#     - postgres_replica_data:/var/lib/postgresql/data
#   environment:
#     POSTGRES_DB: ai_tutor
#     POSTGRES_USER: replicator
#     POSTGRES_PASSWORD: replicator_password
```

### 3. Redis Configuration

#### Redis Cluster (Production)
```yaml
# docker-compose.prod.yml
redis-node1:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
  ports:
    - "7001:6379"
  volumes:
    - redis_data1:/data

redis-node2:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
  ports:
    - "7002:6379"
  volumes:
    - redis_data2:/data

redis-node3:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
  ports:
    - "7003:6379"
  volumes:
    - redis_data3:/data
```

### 4. Load Balancer Setup (Nginx)

#### nginx.conf
```nginx
upstream api_servers {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name ai-tutor.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai-tutor.com;

    ssl_certificate /etc/ssl/certs/ai-tutor.crt;
    ssl_certificate_key /etc/ssl/private/ai-tutor.key;

    # WebSocket support
    location /ws {
        proxy_pass http://api_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API endpoints
    location /api {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static {
        alias /var/www/ai-tutor/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 5. SSL Certificate (Let's Encrypt)
```bash
# Install Certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d ai-tutor.com -d www.ai-tutor.com

# Auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

### 6. Monitoring Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

#### Grafana Dashboards
1. Import dashboard templates from `monitoring/grafana/dashboards/`
2. Set up alerts for:
   - High error rates (>5%)
   - High response times (>1s)
   - Database connection issues
   - Redis memory usage (>80%)

### 7. Backup Strategy

#### Database Backups
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres ai_tutor | gzip > $BACKUP_DIR/ai_tutor_$DATE.sql.gz

# Backup Redis
docker-compose exec redis redis-cli --rdb /data/dump.rdb
docker cp ai-tutor-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Rotate old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete
```

#### Schedule with Cron
```bash
# Daily backup at 2 AM
0 2 * * * /opt/ai-tutor/scripts/backup.sh
```

### 8. Scaling Strategy

#### Horizontal Scaling
```yaml
# Scale API servers
docker-compose up -d --scale api=4

# Scale workers
docker-compose up -d --scale worker=8
```

#### Database Scaling
1. **Read Replicas**: For read-heavy workloads
2. **Connection Pooling**: Use PgBouncer
3. **Partitioning**: Use TimescaleDB hypertables

#### Redis Scaling
1. **Redis Cluster**: For high availability
2. **Redis Sentinel**: For automatic failover

### 9. Security Hardening

#### Docker Security
```bash
# Run as non-root user
docker-compose exec api whoami  # Should show 'appuser'

# Enable security options
services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

#### Network Security
```bash
# Create internal network
docker network create --internal ai-tutor-internal

# Only expose necessary ports
ports:
  - "443:443"  # HTTPS only
```

#### Application Security
1. **Rate Limiting**: Enable in `.env`
2. **CORS**: Configure allowed origins
3. **Input Validation**: Use Pydantic models
4. **SQL Injection**: Use SQLAlchemy ORM
5. **XSS Protection**: Sanitize user input

### 10. Performance Optimization

#### Database Optimization
```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_sessions_user_date ON learning_sessions(user_id, start_time DESC);
CREATE INDEX CONCURRENTLY idx_interactions_session_time ON session_interactions(session_id, timestamp DESC);

-- Vacuum and analyze regularly
VACUUM ANALYZE learning_sessions;
```

#### Redis Optimization
```bash
# Configure Redis memory policy
maxmemory 2gb
maxmemory-policy allkeys-lru
```

#### API Optimization
1. **Caching**: Use Redis for frequent queries
2. **Compression**: Enable GZIP middleware
3. **Connection Pooling**: Configure database and Redis pools
4. **Async Operations**: Use async/await for I/O operations

### 11. Disaster Recovery

#### Backup Verification
```bash
# Test backup restoration
gunzip -c backup.sql.gz | docker-compose exec -T postgres psql -U postgres ai_tutor_test
```

#### Failover Procedure
1. **Database Failover**:
   ```bash
   # Promote replica
   docker-compose exec postgres-replica pg_ctl promote
   
   # Update connection strings
   sed -i 's/postgres:5432/postgres-replica:5432/g' .env
   docker-compose restart api worker
   ```

2. **Redis Failover**:
   ```bash
   # Use Redis Sentinel for automatic failover
   # Or manually switch to replica
   ```

### 12. Maintenance Procedures

#### Zero-Downtime Deployments
```bash
# Blue-green deployment
docker-compose -f docker-compose.prod.yml up -d --scale api=4
# Wait for new instances to be healthy
docker-compose -f docker-compose.prod.yml up -d --scale api=8
docker-compose -f docker-compose.prod.yml up -d --scale api=4
# Remove old instances
```

#### Database Migrations
```bash
# Run migrations with zero downtime
docker-compose exec api alembic upgrade head

# Rollback if needed
docker-compose exec api alembic downgrade -1
```

### 13. Monitoring and Alerting

#### Key Metrics to Monitor
1. **API**: Request rate, error rate, response time
2. **Database**: Connection count, query performance, replication lag
3. **Redis**: Memory usage, hit rate, connection count
4. **System**: CPU, memory, disk I/O, network

#### Alert Configuration
```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'slack-notifications'

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '#alerts'
    send_resolved: true
```

### 14. Cost Optimization

#### Cloud Cost Management
1. **Right-sizing**: Monitor and adjust instance sizes
2. **Reserved Instances**: For predictable workloads
3. **Spot Instances**: For non-critical workloads
4. **Auto-scaling**: Scale down during off-peak hours

#### Storage Optimization
1. **Data Retention**: Archive old data to cold storage
2. **Compression**: Enable database and file compression
3. **Deduplication**: Remove duplicate files

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check database status
docker-compose exec postgres pg_isready -U postgres

# Check connection count
docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 2. Redis Memory Issues
```bash
# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Clear cache if needed
docker-compose exec redis redis-cli FLUSHALL
```

#### 3. API Performance Issues
```bash
# Check slow queries
docker-compose exec postgres psql -U postgres -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check API logs
docker-compose logs --tail=100 api
```

#### 4. WebSocket Connection Issues
```bash
# Check WebSocket connections
docker-compose exec redis redis-cli keys "ws:*" | wc -l

# Check WebSocket logs
docker-compose logs --tail=50 api | grep -i websocket
```

### Debug Commands
```bash
# View all logs
docker-compose logs -f

# Check service health
docker-compose ps

# Enter container shell
docker-compose exec api bash

# Check network connectivity
docker-compose exec api curl -I http://postgres:5432
docker-compose exec api curl -I http://redis:6379
```

## Support

### Getting Help
1. **Documentation**: Check `/docs` endpoint
2. **Logs**: View application logs in `logs/` directory
3. **Metrics**: Check Prometheus and Grafana dashboards
4. **Community**: Join our Discord/Slack channel

### Reporting Issues
1. Check existing issues on GitHub
2. Include logs and error messages
3. Provide steps to reproduce
4. Include environment details

## Updates and Maintenance

### Regular Maintenance Tasks
1. **Daily**: Check logs, monitor metrics, verify backups
2. **Weekly**: Update dependencies, clean up old data
3. **Monthly**: Security patches, performance review
4. **Quarterly**: Major updates, architecture review

### Update Procedure
```bash
# Pull latest changes
git pull origin main

# Update dependencies
docker-compose exec api pip install -r requirements.txt

# Run migrations
docker-compose exec api alembic upgrade head

# Restart services
docker-compose restart
```

## License

This deployment guide is part of the NextGen AI Tutor platform. See LICENSE file for details.

---

**Note**: This is a comprehensive deployment guide. Adjust based on your specific infrastructure and requirements. Always test in staging before deploying to production.