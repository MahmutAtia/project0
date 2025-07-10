#!/bin/bash
# filepath: /c:/Users/Attia/careerflow/project0/deploy.sh

# Enhanced Deployment Script for CareerFlow with Let's Encrypt SSL
# Run this script from outside the project directory

# Exit on any error
set -e

# --- Configuration ---
BACKEND_REPO="https://github.com/MahmutAtia/project0.git"
FRONTEND_REPO="https://github.com/MahmutAtia/proj0_front.git"
PROJECT_DIR="prod"
FRONTEND_DIR="careerflow"
BRANCH="prod"
DOMAIN="vbs.attiais.me"

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
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed"
        exit 1
    fi
}

# Verify repository access
verify_repository_access() {
    local repo_url="$1"
    local repo_name="$2"
    
    log_info "Verifying access to $repo_name repository..."
    
    if git ls-remote --heads "$repo_url" >/dev/null 2>&1; then
        log_success "$repo_name repository is accessible"
        
        if git ls-remote --heads "$repo_url" "$BRANCH" | grep -q "$BRANCH"; then
            log_success "Branch '$BRANCH' exists in $repo_name repository"
        else
            log_error "Branch '$BRANCH' does not exist in $repo_name repository"
            log_info "Available branches:"
            git ls-remote --heads "$repo_url" | sed 's/.*refs\/heads\///g' | head -10
            
            log_warning "Would you like to use 'main' branch instead? (y/N)"
            read -p "Choice: " use_main
            if [[ $use_main =~ ^[Yy]$ ]]; then
                BRANCH="main"
                log_info "Switched to 'main' branch"
            else
                exit 1
            fi
        fi
    else
        log_error "Cannot access $repo_name repository: $repo_url"
        log_error "Please check:"
        log_error "1. Repository URL is correct"
        log_error "2. Repository is public or you have access"
        log_error "3. Internet connection is working"
        exit 1
    fi
}

# Generate self-signed certificates
generate_self_signed_certificates() {
    log_info "Generating self-signed SSL certificates..."
    
    mkdir -p nginx/ssl
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/localhost.key \
        -out nginx/ssl/localhost.crt \
        -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost" 2>/dev/null || \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/localhost.key \
        -out nginx/ssl/localhost.crt \
        -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN"
    
    if [ -f "nginx/ssl/localhost.crt" ] && [ -f "nginx/ssl/localhost.key" ]; then
        log_success "Self-signed certificates generated successfully"
        return 0
    else
        log_error "Failed to generate self-signed certificates"
        return 1
    fi
}

# Setup SSL certificates (self-signed first, then optionally Let's Encrypt)
setup_ssl_certificates() {
    log_info "🔒 Setting up SSL certificates..."
    
    cd "$PROJECT_DIR"

    # Check if we already have valid Let's Encrypt certificates
    if check_certificate_status; then
        log_success "✅ Found existing Let's Encrypt certificates"
        log_info "Using existing certificates without changes"
        cd ..
        return 0
    fi
    
    # Always generate self-signed certificates first to ensure nginx can start
    generate_self_signed_certificates || {
        log_error "Failed to generate self-signed certificates"
        exit 1
    }
    
    # Configure nginx to use self-signed certificates initially
    NGINX_CONF="nginx/conf.d/default.conf"
    if [ -f "$NGINX_CONF" ]; then
        # Backup original config
        cp "$NGINX_CONF" "${NGINX_CONF}.backup_$(date +%Y%m%d_%H%M%S)"
        
        # Ensure nginx uses self-signed certificates
        sed -i "s|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|ssl_certificate /etc/nginx/ssl/localhost.crt;|g" "$NGINX_CONF"
        sed -i "s|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|ssl_certificate_key /etc/nginx/ssl/localhost.key;|g" "$NGINX_CONF"
        
        log_success "Nginx configured to use self-signed certificates"
    else
        log_error "Nginx configuration file not found: $NGINX_CONF"
        exit 1
    fi
    
    # Ask user if they want to try Let's Encrypt
    echo
    log_info "SSL Certificate Options:"
    echo "1. Continue with self-signed certificates (browsers will show warnings)"
    echo "2. Try to obtain Let's Encrypt certificates (requires port 80 access)"
    echo
    read -p "Choose option (1-2): " ssl_choice
    
    case $ssl_choice in
        2)
            attempt_letsencrypt_setup || {
                log_warning "Let's Encrypt setup failed, continuing with self-signed certificates"
            }
            ;;
        1|*)
            log_info "Continuing with self-signed certificates"
            ;;
    esac
    
    cd ..
}

# Attempt to setup Let's Encrypt certificates
attempt_letsencrypt_setup() {
    log_info "Attempting Let's Encrypt certificate setup..."
    
    # Create necessary directories
    mkdir -p certbot/conf certbot/www certbot/logs
    
    # Test if port 80 is accessible first
    log_info "Testing port 80 accessibility..."
    
    # Create a minimal nginx config for HTTP challenge only
    cat > nginx/conf.d/letsencrypt-challenge.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files \$uri \$uri/ =404;
    }
    
    location / {
        return 200 'Let\\'s Encrypt Challenge Server Ready';
        add_header Content-Type text/plain;
    }
}
EOF
    
    # Start nginx with challenge configuration
    log_info "Starting nginx for Let's Encrypt challenge..."
    docker compose up -d nginx
    sleep 10
    
    # Test if the challenge endpoint is accessible
    if docker compose exec nginx curl -f "http://localhost/.well-known/acme-challenge/test" >/dev/null 2>&1; then
        log_success "HTTP challenge endpoint is accessible"
    else
        log_warning "HTTP challenge endpoint test failed"
    fi
    
    # Request Let's Encrypt certificate
    log_info "Requesting Let's Encrypt certificate..."
    if docker compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "admin@$DOMAIN" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "$DOMAIN"; then
        
        log_success "Let's Encrypt certificate obtained successfully!"
        
        # Remove challenge config
        rm -f nginx/conf.d/letsencrypt-challenge.conf
        
        # Update main nginx config to use Let's Encrypt certificates
        log_info "Updating nginx to use Let's Encrypt certificates..."
        sed -i "s|ssl_certificate /etc/nginx/ssl/localhost.crt;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|g" "$NGINX_CONF"
        sed -i "s|ssl_certificate_key /etc/nginx/ssl/localhost.key;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|g" "$NGINX_CONF"
        
        # Test nginx configuration
        if docker compose exec nginx nginx -t >/dev/null 2>&1; then
            docker compose restart nginx
            log_success "Nginx restarted with Let's Encrypt certificates"
            setup_ssl_renewal
            return 0
        else
            log_error "Nginx configuration test failed with Let's Encrypt certificates"
            log_warning "Reverting to self-signed certificates..."
            sed -i "s|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|ssl_certificate /etc/nginx/ssl/localhost.crt;|g" "$NGINX_CONF"
            sed -i "s|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|ssl_certificate_key /etc/nginx/ssl/localhost.key;|g" "$NGINX_CONF"
            docker compose restart nginx
            return 1
        fi
    else
        log_error "Let's Encrypt certificate request failed"
        log_error "Common issues:"
        log_error "1. Port 80 is not accessible from the internet"
        log_error "2. DNS is not pointing to this server"
        log_error "3. Domain is not publicly reachable"
        log_error "4. Firewall is blocking port 80"
        
        # Remove challenge config and restart nginx
        rm -f nginx/conf.d/letsencrypt-challenge.conf
        docker compose restart nginx
        
        return 1
    fi
}

# Setup SSL certificate auto-renewal
setup_ssl_renewal() {
    log_info "Setting up SSL certificate auto-renewal..."
    
    cat > renew-ssl.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "Starting SSL certificate renewal: $(date)" >> ssl-renewal.log
if docker compose run --rm certbot renew --quiet; then
    docker compose restart nginx
    echo "SSL certificates renewed successfully: $(date)" >> ssl-renewal.log
else
    echo "SSL certificate renewal failed: $(date)" >> ssl-renewal.log
fi
EOF
    
    chmod +x renew-ssl.sh
    
    log_success "SSL auto-renewal script created: $PROJECT_DIR/renew-ssl.sh"
    log_info "Add this to crontab for automatic renewal:"
    log_info "0 12 * * * cd $(pwd) && ./renew-ssl.sh"
}

# Django management commands
run_django_command() {
    local command="$1"
    log_info "Running Django command: $command"
    docker compose run --rm django python manage.py "$command"
}

# Database management functions
check_database_status() {
    log_info "Checking database connection..."
    if docker compose run --rm django python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proj0.settings')
import django
django.setup()
from django.db import connection
connection.ensure_connection()
print('Database OK')
" >/dev/null 2>&1; then
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
    
    # Create and apply migrations
    log_migration "Creating new migrations..."
    docker compose run --rm django python manage.py makemigrations || log_warning "No new migrations needed"
    
    log_migration "Applying migrations..."
    docker compose run --rm django python manage.py migrate || {
        log_error "Migration failed!"
        exit 1
    }
    
    log_success "All migrations completed successfully"
}

setup_initial_data() {
    log_data "Setting up initial application data..."
    
    log_data "Creating application features..."
    docker compose run --rm django python manage.py create_features || {
        log_warning "Feature creation failed, but continuing..."
    }
    
    log_data "Creating subscription plans..."
    docker compose run --rm django python manage.py create_plans || {
        log_warning "Plan creation failed, but continuing..."
    }
    
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
    log_info "Downloading external assets..."
    if [ -f "$PROJECT_DIR/django/script.py" ]; then
        docker compose run --rm django python script.py || {
            log_warning "External assets download failed, but continuing..."
        }
        log_success "External assets downloaded"
    else
        log_warning "Asset download script not found, skipping..."
    fi
}


check_certificate_status() {
    # Check if certificates exist in the Docker volume
    if docker compose run --rm certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
        return 0  # Certificate exists
    else
        return 1  # No certificate found
    fi
}

# Replace ONLY the SSL certificate check part in run_health_checks() function:

run_health_checks() {
    log_info "Running application health checks..."
    
    # Check database connection
    if check_database_status; then
        log_success "✅ Database connection: OK"
    else
        log_error "❌ Database connection: FAILED"
    fi
    
    # Check Django application
    log_info "Checking Django application..."
    if docker compose run --rm django python manage.py check --deploy >/dev/null 2>&1; then
        log_success "✅ Django application: OK"
    else
        log_warning "⚠️  Django application: Has warnings"
    fi
    
    # Check SSL certificates - REPLACE THIS SECTION ONLY
    log_info "Checking SSL certificate..."
    cd "$PROJECT_DIR"
    if check_certificate_status; then
        log_success "✅ Let's Encrypt SSL certificate: OK"
    elif [ -f "$PROJECT_DIR/nginx/ssl/localhost.crt" ]; then
        log_warning "⚠️  Self-signed SSL certificate: OK (browser warnings expected)"
    else
        log_error "❌ No SSL certificate found"
    fi
    
    # Check service status
    log_info "Checking service status..."
    docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
}

# Add this function after restart_services() but before the main function call:

check_certificates() {
    cd "$PROJECT_DIR"
    log_info "Checking SSL certificates..."
    docker compose run --rm certbot certificates
    cd ..
}

# Main deployment function
main() {
    echo "🚀 Starting CareerFlow deployment..."
    echo "=================================================="
    log_info "Working directory: $(pwd)"
    log_info "Target domain: $DOMAIN"
    log_info "Target branch: $BRANCH"
    echo
    
    # Step 1: Check tools
    log_info "Step 1: Checking required tools..."
    check_tool git
    check_tool docker
    check_tool openssl
    log_success "All tools are available"
    echo
    
    # Step 2: Verify repositories
    log_info "Step 2: Verifying repository access..."
    verify_repository_access "$BACKEND_REPO" "Backend"
    verify_repository_access "$FRONTEND_REPO" "Frontend"
    echo
    
    # Step 3: Handle backend repository
    log_info "Step 3: Managing backend repository..."
    if [ -d "$PROJECT_DIR" ]; then
        log_info "Updating existing backend..."
        cd "$PROJECT_DIR"
        
        if [ ! -d ".git" ]; then
            cd ..
            rm -rf "$PROJECT_DIR"
            git clone -b "$BRANCH" "$BACKEND_REPO" "$PROJECT_DIR"
        else
            git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
            git reset --hard "origin/$BRANCH"
        fi
        cd ..
    else
        git clone -b "$BRANCH" "$BACKEND_REPO" "$PROJECT_DIR"
    fi
    log_success "Backend repository ready"
    echo
    
    # Step 4: Handle frontend repository
    log_info "Step 4: Managing frontend repository..."
    FRONTEND_PATH="$PROJECT_DIR/$FRONTEND_DIR"
    
    if [ -d "$FRONTEND_PATH" ]; then
        cd "$FRONTEND_PATH"
        if [ ! -d ".git" ]; then
            cd ../..
            rm -rf "$FRONTEND_PATH"
            cd "$PROJECT_DIR"
            git clone -b "$BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR"
            cd ..
        else
            git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
            git reset --hard "origin/$BRANCH"
            cd ../..
        fi
    else
        cd "$PROJECT_DIR"
        git clone -b "$BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR"
        cd ..
    fi
    
    # Verify frontend content
    if [ ! -f "$FRONTEND_PATH/package.json" ]; then
        log_error "Frontend repository is invalid or empty"
        exit 1
    fi
    
    log_success "Frontend repository ready"
    echo
    
    # Step 5: Check environment
    log_info "Step 5: Checking environment configuration..."
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_error "Environment file not found at $PROJECT_DIR/.env"
        exit 1
    fi
    log_success "Environment configuration found"
    echo
    
    # Step 6: Setup SSL certificates (BEFORE starting any services)
    log_info "Step 6: Setting up SSL certificates..."
    setup_ssl_certificates
    echo
    
    # Step 7: Build images
    log_info "Step 7: Building Docker images..."
    cd "$PROJECT_DIR"
    docker compose build
    log_success "Docker images built"
    cd ..
    echo
    
    # Step 8: Start core services
    log_info "Step 8: Starting core services..."
    cd "$PROJECT_DIR"
    docker compose up -d db redis
    sleep 15
    log_success "Core services started"
    echo
    
    # Step 9: Run migrations
    log_info "Step 9: Running database migrations..."
    run_migrations
    echo
    
    # Step 10: Setup data
    log_info "Step 10: Setting up application data..."
    setup_initial_data
    echo
    
    # Step 11: External assets
    log_info "Step 11: Downloading external assets..."
    download_external_assets
    echo
    
    # Step 12: Static files
    log_info "Step 12: Collecting static files..."
    collect_static_files
    echo
    
    # Step 13: Superuser
    log_info "Step 13: Setting up superuser..."
    create_superuser
    echo
    
    # Step 14: Start all services
    log_info "Step 14: Starting all services..."
    docker compose up -d
    sleep 15
    log_success "All services started"
    echo
    
    # Step 15: Health checks
    log_info "Step 15: Running health checks..."
    run_health_checks
    echo
    
    cd ..
    
    # Show completion summary
    echo "=================================================="
    log_success "🎉 CareerFlow Deployment Completed!"
    echo "=================================================="
    echo
    log_info "🌐 Application URLs:"
    log_info "• HTTP:  http://$DOMAIN:880"
    log_info "• HTTPS: https://$DOMAIN:8443"
    log_info "• Admin: https://$DOMAIN:8443/admin/"
    echo
    
    if check_certificate_status; then
        log_success "✅ Using trusted Let's Encrypt certificates"
    else
        log_warning "⚠️  Using self-signed certificates (browser warnings expected)"
    fi
    
    echo
    log_info "📋 Next Steps:"
    log_info "1. Test your application in a browser"
    log_info "2. Configure firewall to allow ports 880 and 8443"
    log_info "3. Monitor logs: docker compose logs -f"
    echo
}

# Utility functions
show_logs() {
    cd "$PROJECT_DIR"
    docker compose logs -f --tail=50
}

restart_services() {
    cd "$PROJECT_DIR"
    docker compose restart
    log_success "Services restarted"
    cd ..
}

# Run main deployment
main

# Offer post-deployment actions
echo
log_info "Additional actions:"
echo "1. View logs"
echo "2. Restart services"
echo "3. Check certificates"
echo "4. Exit"
echo
read -p "Choose (1-4): " action
case $action in
    1) show_logs ;;
    2) restart_services ;;
    3) check_certificates ;;
    *) log_info "Deployment complete! 🚀" ;;
esac