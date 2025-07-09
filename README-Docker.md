# Docker Compose Configurations

This project now supports separate configurations for development and production environments.

## Available Configurations

### 1. Development Environment (`docker-compose.dev.yml`)
- Hot reloading for all services
- Debug mode enabled
- Console email backend
- Relaxed security settings
- Volume mounts for live code changes
- Development-friendly ports exposed

### 2. Production Environment (`docker-compose.prod.yml`)
- Optimized for production
- Includes Nginx and SSL (Certbot)
- Health checks for all services
- Gunicorn with multiple workers
- Celery beat scheduler included
- Production security settings

## Usage

### Development Environment

1. **Setup environment variables:**
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with your development settings
   ```

2. **Start development services:**
   ```bash
   # Start all services
   docker-compose -f docker-compose.dev.yml --env-file .env.dev up -d
   
   # Or start specific services (API and Django only)
   docker-compose -f docker-compose.dev.yml --env-file .env.dev up -d api django db redis
   ```

3. **Access services:**
   - Django: http://localhost:8000
   - API: http://localhost:580
   - Frontend: http://localhost:3000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

### Production Environment

1. **Setup environment variables:**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with your production settings
   ```

2. **Start production services:**
   ```bash
   # Start all services
   docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
   
   # Start with SSL (requires domain setup)
   docker-compose -f docker-compose.prod.yml --env-file .env.prod --profile ssl up -d
   ```

3. **Access services:**
   - Application: http://your-domain.com:880 (or https://your-domain.com:8443 with SSL)

## Key Differences Between Environments

| Feature | Development | Production |
|---------|-------------|------------|
| Debug Mode | Enabled | Disabled |
| Code Reloading | Hot reload | Static build |
| Email Backend | Console | SMTP |
| Security | Relaxed | Strict HTTPS/SSL |
| Database | Local volumes | Persistent volumes |
| Logging | Debug level | Info level |
| Health Checks | None | Comprehensive |
| Nginx | Not included | Included with SSL |
| Celery Beat | Not included | Included |

## Environment Variables

Key environment variables that differ between environments:

### Development (.env.dev)
```bash
DEBUG=1
NODE_ENV=development
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

### Production (.env.prod)
```bash
DEBUG=0
NODE_ENV=production
DJANGO_ALLOWED_HOSTS=your-domain.com
NEXT_PUBLIC_BACKEND_URL=https://your-domain.com
NEXTAUTH_URL=https://your-domain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Common Commands

### Development
```bash
# Start only API and Django services
docker-compose -f docker-compose.dev.yml up api django db redis

# View logs
docker-compose -f docker-compose.dev.yml logs -f api django

# Run Django migrations
docker-compose -f docker-compose.dev.yml exec django python manage.py migrate

# Create Django superuser
docker-compose -f docker-compose.dev.yml exec django python manage.py createsuperuser

# Shell into Django container
docker-compose -f docker-compose.dev.yml exec django bash
```

### Production
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery=3

# Update and restart services
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

## Migration from Current Setup

If you were using the original `docker-compose.yml`, you can:

1. **Keep it as-is for production:**
   ```bash
   mv docker-compose.yml docker-compose.prod.yml.backup
   cp docker-compose.prod.yml docker-compose.yml
   ```

2. **Or rename it and use the new structure:**
   ```bash
   mv docker-compose.yml docker-compose.legacy.yml
   # Then use docker-compose.dev.yml or docker-compose.prod.yml as needed
   ```

## Troubleshooting

### Development Issues
- **Port conflicts:** Make sure ports 3000, 8000, 580, 5432, 6379 are available
- **File permissions:** Ensure your user has write access to the project directory
- **Hot reload not working:** Check volume mounts in docker-compose.dev.yml

### Production Issues
- **SSL certificates:** Ensure your domain points to the server before running Certbot
- **Database persistence:** Check that volumes are properly configured
- **Health checks failing:** Review service logs for startup issues

## Security Notes

### Development
- Uses relaxed security settings for easier development
- Database passwords and secrets have defaults
- HTTPS is disabled by default

### Production
- Requires proper SSL certificates
- All security settings are enabled
- All secrets must be properly configured
- Database is isolated (no external ports)

Make sure to:
1. Change all default passwords and secrets
2. Set up proper SSL certificates
3. Configure your firewall appropriately
4. Regularly update container images
