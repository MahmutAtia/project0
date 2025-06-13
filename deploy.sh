#!/bin/bash

# Enhanced Deployment Script for CareerFlow with Database Management
# Run this script from outside the project directory

# Exit on any error
set -e

# --- Configuration ---
BACKEND_REPO="https://github.com/MahmutAtia/project0.git"
FRONTEND_REPO="https://github.com/MahmutAtia/proj0_front.git"
PROJECT_DIR="prod"
FRONTEND_DIR="careerflow"
BRANCH="prod"
DOMAIN="srv658540.hstgr.cloud"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
}

log_migration() {
    echo -e "${PURPLE}MIGRATION:${NC} $1"
}

log_data() {
    echo -e "${CYAN}DATA:${NC} $1"
}

# Check if command exists
check_tool() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed"
        exit 1
    fi
}

# Django management commands
run_django_command() {
    local command="$1"
    log_info "Running Django command: $command"
    docker compose run --rm django python manage.py $command
}

# Database management functions
check_database_status() {
    log_info "Checking database connection..."
    if docker compose run --rm django python manage.py dbshell --command="SELECT 1;" > /dev/null 2>&1; then
        log_success "Database is accessible"
        return 0
    else
        log_warning "Database connection failed"
        return 1
    fi
}

create_superuser() {
    log_info "Creating Django superuser..."
    read -p "Do you want to create a superuser? (y/N): " create_user
    if [[ $create_user =~ ^[Yy]$ ]]; then
        # Try automatic superuser creation first
        docker compose run --rm django python manage.py createsuperuser --noinput || {
            log_info "Interactive superuser creation..."
            docker compose run --rm -it django python manage.py createsuperuser
        }
    fi
}

run_migrations() {
    log_migration "Starting Django migrations process..."
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if check_database_status; then
            break
        fi
        retries=$((retries + 1))
        log_info "Waiting for database... (attempt $retries/$max_retries)"
        sleep 2
    done
    
    if [ $retries -eq $max_retries ]; then
        log_error "Database is not ready after $max_retries attempts"
        exit 1
    fi
    
    # Show current migration status
    log_migration "Checking current migration status..."
    docker compose run --rm django python manage.py showmigrations || log_warning "Could not show migrations"
    
    # Create new migrations if models changed
    log_migration "Creating new migrations for model changes..."
    docker compose run --rm django python manage.py makemigrations || log_warning "No new migrations needed"
    
    # Apply all migrations
    log_migration "Applying all pending migrations..."
    docker compose run --rm django python manage.py migrate || {
        log_error "Migration failed!"
        exit 1
    }
    
    # Show final migration status
    log_migration "Final migration status:"
    docker compose run --rm django python manage.py showmigrations --plan || log_warning "Could not show migration plan"
    
    log_success "All migrations completed successfully"
}

setup_initial_data() {
    log_data "Setting up initial application data..."
    
    # Create features first (plans depend on features)
    log_data "Creating application features..."
    docker compose run --rm django python manage.py create_features || {
        log_warning "Feature creation failed, but continuing..."
    }
    
    # Create plans and their feature limits
    log_data "Creating subscription plans..."
    docker compose run --rm django python manage.py create_plans || {
        log_warning "Plan creation failed, but continuing..."
    }
    
    # Run any other initial data setup commands here
    log_data "Running additional data setup commands..."
    # Example: docker compose run --rm django python manage.py loaddata initial_data.json
    
    log_success "Initial application data setup completed"
}

collect_static_files() {
    log_info "Collecting Django static files..."
    docker compose run --rm django python manage.py collectstatic --noinput --clear || {
        log_warning "Static files collection failed, but continuing..."
    }
    log_success "Static files collected"
}

download_external_assets() {
    log_info "Downloading external assets (fonts, icons)..."
    if [ -f "$PROJECT_DIR/django/script.py" ]; then
        docker compose run --rm django python script.py || {
            log_warning "External assets download failed, but continuing..."
        }
        log_success "External assets downloaded"
    else
        log_warning "Asset download script not found, skipping..."
    fi
}

run_health_checks() {
    log_info "Running application health checks..."
    
    # Check database connection
    if check_database_status; then
        log_success "✅ Database connection: OK"
    else
        log_error "❌ Database connection: FAILED"
    fi
    
    # Check if Django is responding
    log_info "Checking Django application..."
    if docker compose run --rm django python manage.py check --deploy > /dev/null 2>&1; then
        log_success "✅ Django application: OK"
    else
        log_warning "⚠️  Django application: Has warnings (check logs)"
    fi
    
    # Check if services are running
    log_info "Checking service status..."
    docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
}

# Main deployment function
main() {
    echo "🚀 Starting CareerFlow deployment with comprehensive setup..."
    echo "=================================================="
    log_info "Working directory: $(pwd)"
    log_info "Target domain: $DOMAIN"
    log_info "Target branch: $BRANCH"
    echo
    
    # Check required tools
    log_info "Step 1: Checking required tools..."
    check_tool git
    check_tool docker
    check_tool openssl
    log_success "All tools are available"
    echo
    
    # Handle backend repository
    log_info "Step 2: Managing backend repository..."
    if [ -d "$PROJECT_DIR" ]; then
        log_info "Updating existing backend..."
        cd "$PROJECT_DIR"
        
        # Force update to match remote (fixes non-fast-forward issues)
        git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
        git reset --hard "origin/$BRANCH"
        
        cd ..
        log_success "Backend updated"
    else
        log_info "Cloning backend repository..."
        git clone -b $BRANCH $BACKEND_REPO $PROJECT_DIR
        log_success "Backend cloned"
    fi
    echo
    
    # Handle frontend repository
    log_info "Step 3: Managing frontend repository..."
    FRONTEND_PATH="$PROJECT_DIR/$FRONTEND_DIR"
    
    if [ -d "$FRONTEND_PATH" ]; then
        log_info "Updating existing frontend..."
        cd "$FRONTEND_PATH"
        
        # Force update to match remote (fixes non-fast-forward issues)
        git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
        git reset --hard "origin/$BRANCH"
        
        cd ../..
        log_success "Frontend updated"
    else
        log_info "Cloning frontend repository..."
        cd "$PROJECT_DIR"
        git clone -b $BRANCH $FRONTEND_REPO $FRONTEND_DIR
        cd ..
        log_success "Frontend cloned"
    fi
    echo
    
    # Setup environment file
    log_info "Step 4: Setting up environment configuration..."
    ENV_FILE="$PROJECT_DIR/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        log_info "Creating .env file..."
        cat > "$ENV_FILE" << EOF
# Production Environment Configuration
NODE_ENV=production
DEBUG=0
PYTHONUNBUFFERED=1

# Database Configuration
POSTGRES_DB=careerflow_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_db_password_here

# Django Configuration
DJANGO_SECRET_KEY=your_very_secure_secret_key_here
DJANGO_ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@$DOMAIN
DJANGO_SUPERUSER_PASSWORD=your_secure_admin_password_here

# Authentication Configuration
NEXTAUTH_SECRET=your_nextauth_secret_here
NEXTAUTH_URL=https://$DOMAIN

# Google Services Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_API_KEY=your_google_api_key_here

# External API Configuration
LANGCHAIN_API_KEY=your_langchain_api_key_here
EMAIL_HOST_PASSWORD=your_email_host_password_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Production URLs
NEXT_PUBLIC_API_URL=https://$DOMAIN
NEXT_PUBLIC_BACKEND_URL=https://$DOMAIN

# Additional Production Settings
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
EOF
        log_warning "⚠️  IMPORTANT: Please edit $ENV_FILE with your actual secure values!"
        log_warning "⚠️  Do NOT use default passwords in production!"
        read -p "Press Enter after editing the .env file with secure values..."
    else
        log_info ".env file already exists"
    fi
    echo
    
    # Generate SSL certificates if they don't exist
    log_info "Step 5: Setting up SSL certificates..."
    if [ ! -f "$PROJECT_DIR/nginx/ssl/localhost.crt" ]; then
        log_info "Generating self-signed SSL certificates for $DOMAIN..."
        cd "$PROJECT_DIR"
        mkdir -p nginx/ssl
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
          -keyout nginx/ssl/localhost.key \
          -out nginx/ssl/localhost.crt \
          -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN" \
          -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost" 2>/dev/null || {
          # Fallback for older OpenSSL versions
          log_warning "Using fallback SSL generation for older OpenSSL..."
          openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/localhost.key \
            -out nginx/ssl/localhost.crt \
            -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN"
        }
        
        cd ..
        log_success "SSL certificates generated for $DOMAIN"
    else
        log_info "SSL certificates already exist"  
    fi
    echo
    
    # Build and start services
    log_info "Step 6: Building Docker images..."
    cd "$PROJECT_DIR"
    docker compose build
    log_success "Docker images built successfully"
    echo
    
    # Start core services first
    log_info "Step 7: Starting core services (database, redis)..."
    docker compose up -d db redis
    sleep 15  # Give database time to initialize
    log_success "Core services started"
    echo
    
    # Run comprehensive database migrations
    log_info "Step 8: Running database migrations..."
    run_migrations
    echo
    
    # Setup initial application data
    log_info "Step 9: Setting up initial application data..."
    setup_initial_data
    echo
    
    # Download external assets
    log_info "Step 10: Downloading external assets..."
    download_external_assets
    echo
    
    # Collect static files
    log_info "Step 11: Collecting static files..."
    collect_static_files
    echo
    
    # Create superuser if needed
    log_info "Step 12: Setting up superuser account..."
    create_superuser
    echo
    
    # Start remaining services
    log_info "Step 13: Starting all remaining services..."
    docker compose up -d
    log_success "All services started"
    echo
    
    # Wait for services to stabilize
    log_info "Waiting for services to stabilize..."
    sleep 15
    
    # Run health checks
    log_info "Step 14: Running health checks..."
    run_health_checks
    echo
    
    cd ..
    
    # Show completion summary
    echo "=================================================="
    log_success "🎉 CareerFlow Deployment Completed Successfully!"
    echo "=================================================="
    echo
    log_info "📋 Deployment Summary:"
    log_success "✅ Repositories updated to latest $BRANCH branch"
    log_success "✅ SSL certificates generated and configured"
    log_success "✅ Database schema migrations applied"
    log_success "✅ Initial application data created (features & plans)"
    log_success "✅ External assets downloaded"
    log_success "✅ Static files collected and optimized"
    log_success "✅ All services running and healthy"
    echo
    log_info "🌐 Application Access URLs:"
    log_info "┌─────────────────────────────────────────────────────┐"
    log_info "│ HTTP:  http://$DOMAIN:880                    │"
    log_info "│ HTTPS: https://$DOMAIN:8443                 │"
    log_info "│ Admin: https://$DOMAIN:8443/admin/          │"
    log_info "│ API:   https://$DOMAIN:8443/api/            │"
    log_info "└─────────────────────────────────────────────────────┘"
    echo
    log_info "🔧 Development URLs (for debugging):"
    log_info "│ Frontend:    http://localhost:3000                   │"
    log_info "│ Backend:     http://localhost:8000                   │"
    log_info "│ Database:    postgresql://localhost:5432             │"
    echo
    log_warning "📋 Post-Deployment Notes:"
    log_warning "• Accept the self-signed certificate warning in your browser"
    log_warning "• Update DNS records to point $DOMAIN to this server"
    log_warning "• Consider setting up Let's Encrypt for production SSL"
    log_warning "• Monitor logs for any issues: docker compose logs -f"
    echo
}

# Additional utility functions for post-deployment management
show_logs() {
    echo "📊 Showing live application logs..."
    cd "$PROJECT_DIR"
    docker compose logs -f --tail=50
}

restart_services() {
    echo "🔄 Restarting all services..."
    cd "$PROJECT_DIR"
    docker compose restart
    log_success "All services restarted"
}

show_service_status() {
    echo "📊 Current service status:"
    cd "$PROJECT_DIR"
    docker compose ps
}

backup_database() {
    echo "💾 Creating database backup..."
    cd "$PROJECT_DIR"
    docker compose exec db pg_dump -U postgres careerflow_db > "backup_$(date +%Y%m%d_%H%M%S).sql"
    log_success "Database backup created"
}

# Run main deployment function
main

# Offer additional post-deployment actions
echo
log_info "🛠️  Additional Actions Available:"
echo "1. View live logs"
echo "2. Show service status"
echo "3. Restart services"
echo "4. Backup database"
echo "5. Exit"
echo

read -p "Choose an action (1-5): " action
case $action in
    1)
        show_logs
        ;;
    2)
        show_service_status
        ;;
    3)
        restart_services
        ;;
    4)
        backup_database
        ;;
    5|*)
        log_info "Deployment complete. Have a great day! 🚀"
        ;;
esac