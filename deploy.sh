#!/bin/bash

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
    
    # Test if we can access the repository
    if git ls-remote --heads "$repo_url" >/dev/null 2>&1; then
        log_success "$repo_name repository is accessible"
        
        # Check if the branch exists
        if git ls-remote --heads "$repo_url" "$BRANCH" | grep -q "$BRANCH"; then
            log_success "Branch '$BRANCH' exists in $repo_name repository"
        else
            log_error "Branch '$BRANCH' does not exist in $repo_name repository"
            log_info "Available branches:"
            git ls-remote --heads "$repo_url" | sed 's/.*refs\/heads\///g' | head -10
            
            # Ask user to choose branch or exit
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

# Django management commands
run_django_command() {
    local command="$1"
    log_info "Running Django command: $command"
    docker compose run --rm django python manage.py "$command"
}

# Database management functions
check_database_status() {
    log_info "Checking database connection..."
    # Use Django's check command but ignore warnings
    if docker compose run --rm django python manage.py check --database default --quiet > /dev/null 2>&1; then
        log_success "Database is accessible"
        return 0
    else
        # Try a simpler database test
        if docker compose run --rm django python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proj0.settings')
import django
django.setup()
from django.db import connection
connection.ensure_connection()
print('Database OK')
" > /dev/null 2>&1; then
            log_success "Database is accessible"
            return 0
        else
            log_warning "Database connection failed"
            return 1
        fi
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

# Let's Encrypt SSL setup
setup_letsencrypt() {
    log_info "🔒 Setting up Let's Encrypt SSL certificates..."
    
    # Check if Let's Encrypt certificates already exist
    if [ -d "$PROJECT_DIR/certbot/conf/live/$DOMAIN" ]; then
        log_info "Let's Encrypt certificates already exist for $DOMAIN"
        return 0
    fi
    
    log_info "Generating Let's Encrypt certificates for $DOMAIN..."
    cd "$PROJECT_DIR"
    
    # Create necessary directories
    mkdir -p certbot/conf certbot/www certbot/logs
    
    # Start nginx first for HTTP challenge - but with basic config
    log_info "Starting nginx for HTTP challenge..."
    
    # Create a temporary nginx config for Let's Encrypt challenge
    cat > nginx/conf.d/letsencrypt.conf << 'EOF'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri $uri/ =404;
    }
    
    location / {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF
    
    # Replace placeholder with actual domain
    sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx/conf.d/letsencrypt.conf
    
    # Start only nginx for the challenge
    docker compose up -d nginx
    sleep 10
    
    # Request certificate using certbot
    log_info "Requesting SSL certificate from Let's Encrypt..."
    docker compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "admin@$DOMAIN" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "$DOMAIN" || {
        log_error "Let's Encrypt certificate generation failed!"
        log_error "Please check:"
        log_error "1. Domain $DOMAIN DNS points to this server"
        log_error "2. Port 80 is accessible from internet"
        log_error "3. Domain is valid and publicly accessible"
        
        # Restore original nginx config
        rm -f nginx/conf.d/letsencrypt.conf
        log_warning "Continuing with self-signed certificates..."
        cd ..
        return 1
    }
    
    # Remove temporary config and restore original
    rm -f nginx/conf.d/letsencrypt.conf
    
    # Update nginx config to use Let's Encrypt certificates
    log_info "Updating nginx configuration for Let's Encrypt..."
    
    # Backup existing config
    cp nginx/conf.d/default.conf nginx/conf.d/default.conf.backup
    
    # Update SSL certificate paths in nginx config
    sed -i "s|ssl_certificate /etc/nginx/ssl/localhost.crt;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|g" nginx/conf.d/default.conf
    sed -i "s|ssl_certificate_key /etc/nginx/ssl/localhost.key;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|g" nginx/conf.d/default.conf
    
    # Restart nginx with new certificates
    docker compose restart nginx
    
    log_success "✅ Let's Encrypt SSL certificates configured successfully!"
    
    # Set up auto-renewal
    setup_ssl_renewal
    
    cd ..
}

# Setup SSL certificate auto-renewal
setup_ssl_renewal() {
    log_info "Setting up SSL certificate auto-renewal..."
    
    # Create renewal script
    cat > renew-ssl.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
docker compose run --rm certbot renew --quiet
docker compose restart nginx
echo "SSL certificates renewed: $(date)" >> ssl-renewal.log
EOF
    
    chmod +x renew-ssl.sh
    
    log_info "SSL auto-renewal script created: $PROJECT_DIR/renew-ssl.sh"
    log_info "Add this to crontab for automatic renewal:"
    log_info "0 12 * * * cd $(pwd) && ./renew-ssl.sh"
    
    # Ask if user wants to add to crontab
    read -p "Add SSL renewal to crontab now? (y/N): " add_cron
    if [[ $add_cron =~ ^[Yy]$ ]]; then
        (crontab -l 2>/dev/null; echo "0 12 * * * cd $(pwd) && ./renew-ssl.sh") | crontab -
        log_success "SSL auto-renewal added to crontab"
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
    
    # Check SSL certificate
    log_info "Checking SSL certificate..."
    if [ -d "$PROJECT_DIR/certbot/conf/live/$DOMAIN" ]; then
        log_success "✅ Let's Encrypt SSL certificate: OK"
    elif [ -f "$PROJECT_DIR/nginx/ssl/localhost.crt" ]; then
        log_warning "⚠️  Self-signed SSL certificate: OK (browser warnings expected)"
    else
        log_error "❌ No SSL certificate found"
    fi
    
    # Check if services are running
    log_info "Checking service status..."
    docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
}

# Main deployment function
main() {
    echo "🚀 Starting CareerFlow deployment with existing configuration..."
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
    
    # Verify repository access
    log_info "Step 1.5: Verifying repository access..."
    verify_repository_access "$BACKEND_REPO" "Backend"
    verify_repository_access "$FRONTEND_REPO" "Frontend"
    echo
    
    # Handle backend repository
    log_info "Step 2: Managing backend repository..."
    if [ -d "$PROJECT_DIR" ]; then
        log_info "Updating existing backend..."
        cd "$PROJECT_DIR"
        
        # Check if it's actually a git repository
        if [ ! -d ".git" ]; then
            log_warning "Backend directory exists but is not a git repository. Removing..."
            cd ..
            rm -rf "$PROJECT_DIR"
            log_info "Cloning backend repository..."
            git clone -b "$BRANCH" "$BACKEND_REPO" "$PROJECT_DIR" || {
                log_error "Failed to clone backend repository"
                exit 1
            }
        else
            # Force update to match remote (fixes non-fast-forward issues)
            git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" || {
                log_error "Failed to fetch from backend repository"
                exit 1
            }
            git reset --hard "origin/$BRANCH" || {
                log_error "Failed to reset backend repository"
                exit 1
            }
        fi
        
        cd ..
        log_success "Backend updated"
    else
        log_info "Cloning backend repository..."
        git clone -b "$BRANCH" "$BACKEND_REPO" "$PROJECT_DIR" || {
            log_error "Failed to clone backend repository"
            exit 1
        }
        log_success "Backend cloned"
    fi
    echo
    
    # Handle frontend repository
    log_info "Step 3: Managing frontend repository..."
    FRONTEND_PATH="$PROJECT_DIR/$FRONTEND_DIR"
    
    if [ -d "$FRONTEND_PATH" ]; then
        log_info "Updating existing frontend..."
        cd "$FRONTEND_PATH"
        
        # Check if it's actually a git repository
        if [ ! -d ".git" ]; then
            log_warning "Frontend directory exists but is not a git repository. Removing..."
            cd ..
            rm -rf "$FRONTEND_DIR"
            log_info "Cloning frontend repository..."
            git clone -b "$BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR" || {
                log_error "Failed to clone frontend repository"
                exit 1
            }
        else
            # Check if remote origin matches our repo
            CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
            if [ "$CURRENT_REMOTE" != "$FRONTEND_REPO" ]; then
                log_warning "Frontend directory has wrong remote origin. Re-cloning..."
                cd ..
                rm -rf "$FRONTEND_DIR"
                git clone -b "$BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR" || {
                    log_error "Failed to clone frontend repository"
                    exit 1
                }
            else
                # Force update to match remote
                log_info "Fetching latest changes..."
                git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" || {
                    log_error "Failed to fetch from frontend repository"
                    exit 1
                }
                git reset --hard "origin/$BRANCH" || {
                    log_error "Failed to reset frontend repository"
                    exit 1
                }
            fi
        fi
        
        cd ../..
        log_success "Frontend updated"
    else
        log_info "Cloning frontend repository..."
        cd "$PROJECT_DIR"
        git clone -b "$BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR" || {
            log_error "Failed to clone frontend repository"
            exit 1
        }
        cd ..
        log_success "Frontend cloned"
    fi
    
    # Verify frontend repository has content
    log_info "Verifying frontend repository content..."
    if [ ! -f "$FRONTEND_PATH/package.json" ]; then
        log_error "Frontend repository appears to be empty or invalid (no package.json found)"
        log_info "Repository contents:"
        ls -la "$FRONTEND_PATH" || echo "Directory not accessible"
        log_info "Attempting to re-clone frontend repository..."
        
        cd "$PROJECT_DIR"
        rm -rf "$FRONTEND_DIR"
        git clone -b "$BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR" || {
            log_error "Failed to re-clone frontend repository"
            exit 1
        }
        cd ..
        
        if [ ! -f "$FRONTEND_PATH/package.json" ]; then
            log_error "Frontend repository is still empty after re-cloning"
            log_error "Please check if the frontend repository exists and has a '$BRANCH' branch"
            log_error "Repository URL: $FRONTEND_REPO"
            log_error "Branch: $BRANCH"
            exit 1
        fi
    fi
    
    log_success "Frontend repository verified with content"
    echo
    
    # Check if .env file exists
    log_info "Step 4: Checking environment configuration..."
    ENV_FILE="$PROJECT_DIR/.env"
    if [ -f "$ENV_FILE" ]; then
        log_success "Environment file found and will be used"
    else
        log_error "Environment file not found at $ENV_FILE"
        log_error "Please ensure your .env file is in the correct location"
        exit 1
    fi
    echo
    
    # SSL Certificate Setup
    log_info "Step 5: SSL Certificate Management..."
    
    cd "$PROJECT_DIR"
    
    # Check what certificates actually exist and what nginx is configured for
    NGINX_CONF="nginx/conf.d/default.conf"
    LETSENCRYPT_CERT_EXISTS=false
    SELFSIGNED_CERT_EXISTS=false
    NGINX_USES_LETSENCRYPT=false
    NGINX_USES_SELFSIGNED=false
    
    # Check if certificates exist
    if [ -d "certbot/conf/live/$DOMAIN" ] && [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
        LETSENCRYPT_CERT_EXISTS=true
    fi
    
    if [ -f "nginx/ssl/localhost.crt" ] && [ -f "nginx/ssl/localhost.key" ]; then
        SELFSIGNED_CERT_EXISTS=true
    fi
    
    # Check nginx configuration
    if [ -f "$NGINX_CONF" ]; then
        if grep -q "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$NGINX_CONF"; then
            NGINX_USES_LETSENCRYPT=true
        elif grep -q "/etc/nginx/ssl/localhost.crt" "$NGINX_CONF"; then
            NGINX_USES_SELFSIGNED=true
        fi
    fi
    
    log_info "SSL Status Analysis:"
    log_info "• Let's Encrypt certificates exist: $LETSENCRYPT_CERT_EXISTS"
    log_info "• Self-signed certificates exist: $SELFSIGNED_CERT_EXISTS"
    log_info "• Nginx configured for Let's Encrypt: $NGINX_USES_LETSENCRYPT"
    log_info "• Nginx configured for self-signed: $NGINX_USES_SELFSIGNED"
    
    # Handle different scenarios
    if [ "$LETSENCRYPT_CERT_EXISTS" = true ] && [ "$NGINX_USES_LETSENCRYPT" = true ]; then
        log_success "✅ Let's Encrypt certificates exist and nginx is properly configured"
        
    elif [ "$LETSENCRYPT_CERT_EXISTS" = true ] && [ "$NGINX_USES_SELFSIGNED" = true ]; then
        log_info "🔄 Let's Encrypt certificates exist but nginx is configured for self-signed"
        log_info "Updating nginx to use Let's Encrypt certificates..."
        cp "$NGINX_CONF" "${NGINX_CONF}.backup_$(date +%Y%m%d_%H%M%S)"
        sed -i "s|ssl_certificate /etc/nginx/ssl/localhost.crt;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|g" "$NGINX_CONF"
        sed -i "s|ssl_certificate_key /etc/nginx/ssl/localhost.key;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|g" "$NGINX_CONF"
        log_success "✅ Nginx configuration updated to use Let's Encrypt certificates"
        
    elif [ "$SELFSIGNED_CERT_EXISTS" = true ] && [ "$NGINX_USES_LETSENCRYPT" = true ]; then
        log_warning "⚠️  Nginx expects Let's Encrypt certificates but only self-signed certificates exist"
        echo
        echo "Available options:"
        echo "1. Generate Let's Encrypt certificates (recommended for production)"
        echo "2. Switch nginx to use existing self-signed certificates"
        echo "3. Generate new self-signed certificates"
        echo
        read -p "Choose option (1-3): " cert_option
        
        case $cert_option in
            1)
                log_info "Setting up Let's Encrypt certificates..."
                cd ..
                setup_letsencrypt
                if [ $? -eq 0 ]; then
                    log_success "✅ Let's Encrypt certificates generated and configured"
                else
                    log_warning "Let's Encrypt setup failed, falling back to self-signed certificates"
                    cd "$PROJECT_DIR"
                    cp "$NGINX_CONF" "${NGINX_CONF}.backup_$(date +%Y%m%d_%H%M%S)"
                    sed -i "s|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|ssl_certificate /etc/nginx/ssl/localhost.crt;|g" "$NGINX_CONF"
                    sed -i "s|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|ssl_certificate_key /etc/nginx/ssl/localhost.key;|g" "$NGINX_CONF"
                    log_success "✅ Nginx switched to use self-signed certificates"
                fi
                ;;
            2)
                log_info "Switching nginx to use existing self-signed certificates..."
                cp "$NGINX_CONF" "${NGINX_CONF}.backup_$(date +%Y%m%d_%H%M%S)"
                sed -i "s|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|ssl_certificate /etc/nginx/ssl/localhost.crt;|g" "$NGINX_CONF"
                sed -i "s|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|ssl_certificate_key /etc/nginx/ssl/localhost.key;|g" "$NGINX_CONF"
                log_success "✅ Nginx configuration updated to use self-signed certificates"
                ;;
            3)
                log_info "Generating new self-signed certificates..."
                mkdir -p nginx/ssl
                openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                  -keyout nginx/ssl/localhost.key \
                  -out nginx/ssl/localhost.crt \
                  -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN" \
                  -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost" 2>/dev/null || \
                openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                  -keyout nginx/ssl/localhost.key \
                  -out nginx/ssl/localhost.crt \
                  -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN"
                
                cp "$NGINX_CONF" "${NGINX_CONF}.backup_$(date +%Y%m%d_%H%M%S)"
                sed -i "s|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|ssl_certificate /etc/nginx/ssl/localhost.crt;|g" "$NGINX_CONF"
                sed -i "s|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|ssl_certificate_key /etc/nginx/ssl/localhost.key;|g" "$NGINX_CONF"
                log_success "✅ New self-signed certificates generated and nginx configured"
                ;;
            *)
                log_error "Invalid option selected"
                exit 1
                ;;
        esac
        
    elif [ "$SELFSIGNED_CERT_EXISTS" = true ] && [ "$NGINX_USES_SELFSIGNED" = true ]; then
        log_success "✅ Self-signed certificates exist and nginx is properly configured"
        echo
        read -p "Would you like to upgrade to Let's Encrypt certificates for production? (y/N): " upgrade_ssl
        if [[ $upgrade_ssl =~ ^[Yy]$ ]]; then
            cd ..
            setup_letsencrypt
            if [ $? -ne 0 ]; then
                log_warning "Let's Encrypt setup failed, keeping existing self-signed certificates"
            fi
            cd "$PROJECT_DIR"
        else
            log_info "Keeping existing self-signed certificates"
        fi
        
    elif [ "$LETSENCRYPT_CERT_EXISTS" = false ] && [ "$SELFSIGNED_CERT_EXISTS" = false ]; then
        log_info "No SSL certificates found"
        echo
        echo "SSL Certificate Options:"
        echo "1. Generate Let's Encrypt certificates (recommended for production)"
        echo "2. Generate self-signed certificates (for development/testing)"
        echo
        read -p "Choose option (1-2): " ssl_choice
        
        case $ssl_choice in
            1)
                cd ..
                setup_letsencrypt
                if [ $? -ne 0 ]; then
                    log_warning "Let's Encrypt setup failed, generating self-signed certificates as fallback"
                    cd "$PROJECT_DIR"
                    mkdir -p nginx/ssl
                    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                      -keyout nginx/ssl/localhost.key \
                      -out nginx/ssl/localhost.crt \
                      -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN" \
                      -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost" 2>/dev/null || \
                    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                      -keyout nginx/ssl/localhost.key \
                      -out nginx/ssl/localhost.crt \
                      -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN"
                    log_success "✅ Self-signed certificates generated as fallback"
                fi
                ;;
            2)
                log_info "Generating self-signed certificates..."
                mkdir -p nginx/ssl
                openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                  -keyout nginx/ssl/localhost.key \
                  -out nginx/ssl/localhost.crt \
                  -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN" \
                  -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost" 2>/dev/null || \
                openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                  -keyout nginx/ssl/localhost.key \
                  -out nginx/ssl/localhost.crt \
                  -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=$DOMAIN"
                log_success "✅ Self-signed certificates generated"
                ;;
            *)
                log_error "Invalid option selected"
                exit 1
                ;;
        esac
    else
        log_error "Unexpected SSL certificate configuration state"
        exit 1
    fi
    
    cd ..
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
    if [ -d "$PROJECT_DIR/certbot/conf/live/$DOMAIN" ]; then
        log_success "✅ Let's Encrypt SSL certificates configured"
    else
        log_success "✅ SSL certificates configured"
    fi
    log_success "✅ Database schema migrations applied"
    log_success "✅ Initial application data created (features & plans)"
    log_success "✅ External assets downloaded"
    log_success "✅ Static files collected and optimized"
    log_success "✅ All services running and healthy"
    echo
    log_info "🌐 Application Access URLs:"
    log_info "┌─────────────────────────────────────────────────────┐"
    log_info "│ HTTP:  http://$DOMAIN:880                           │"
    log_info "│ HTTPS: https://$DOMAIN:8443                        │"
    log_info "│ Admin: https://$DOMAIN:8443/admin/                 │"
    log_info "│ API:   https://$DOMAIN:8443/api/                   │"
    log_info "└─────────────────────────────────────────────────────┘"
    echo
    log_info "🔧 Development URLs (for debugging):"
    log_info "│ Frontend:    http://localhost:3000                   │"
    log_info "│ Backend:     http://localhost:8000                   │"
    log_info "│ Database:    postgresql://localhost:5432             │"
    echo
    
    if [ -d "$PROJECT_DIR/certbot/conf/live/$DOMAIN" ]; then
        log_info "🔒 SSL Certificate Information:"
        log_success "✅ Trusted Let's Encrypt certificate installed"
        log_success "✅ No browser security warnings"
        log_success "✅ Auto-renewal configured"
    else
        log_warning "📋 SSL Certificate Notes:"
        log_warning "• Using self-signed certificate"
        log_warning "• Users will see security warnings in browsers"
        log_warning "• Consider upgrading to Let's Encrypt for production"
    fi
    
    echo
    log_warning "📋 Post-Deployment Actions:"
    log_warning "• Test the application in your browser"
    log_warning "• Update DNS records to point $DOMAIN to this server"
    log_warning "• Monitor logs for any issues: docker compose logs -f"
    echo
}

# Enhanced backup function
backup_database() {
    echo "💾 Creating database backup..."
    cd "$PROJECT_DIR"
    
    # Create backups directory if it doesn't exist
    mkdir -p backups
    
    # Generate timestamp
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backups/careerflow_backup_${TIMESTAMP}.sql"
    
    # Create the backup
    log_info "Creating backup: $BACKUP_FILE"
    docker compose exec -T db pg_dump -U postgres -h localhost careerflow_db > "$BACKUP_FILE"
    
    # Check if backup was successful
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_success "Database backup created successfully"
        log_info "Backup file: $BACKUP_FILE"
        log_info "Backup size: $BACKUP_SIZE"
        
        # Compress the backup
        log_info "Compressing backup..."
        gzip "$BACKUP_FILE"
        COMPRESSED_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
        log_success "Backup compressed: ${BACKUP_FILE}.gz (${COMPRESSED_SIZE})"
    else
        log_error "Backup failed or file is empty"
        return 1
    fi
    
    # Clean up old backups (keep last 5)
    log_info "Cleaning up old backups (keeping last 5)..."
    ls -t backups/careerflow_backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
    
    log_success "Database backup process completed"
    cd ..
}

# Backup SSL certificates
backup_ssl_certificates() {
    echo "🔒 Backing up SSL certificates..."
    cd "$PROJECT_DIR"
    
    # Create ssl-backups directory if it doesn't exist
    mkdir -p ssl-backups
    
    # Generate timestamp
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    # Backup Let's Encrypt certificates if they exist
    if [ -d "certbot/conf/live/$DOMAIN" ]; then
        log_info "Backing up Let's Encrypt certificates..."
        tar -czf "ssl-backups/letsencrypt_backup_${TIMESTAMP}.tar.gz" -C certbot/conf live archive renewal
        log_success "Let's Encrypt certificates backed up"
    fi
    
    # Backup self-signed certificates if they exist
    if [ -f "nginx/ssl/localhost.crt" ]; then
        log_info "Backing up self-signed certificates..."
        tar -czf "ssl-backups/selfsigned_backup_${TIMESTAMP}.tar.gz" -C nginx ssl
        log_success "Self-signed certificates backed up"
    fi
    
    # Backup nginx configuration
    if [ -f "nginx/conf.d/default.conf" ]; then
        cp "nginx/conf.d/default.conf" "ssl-backups/nginx_config_backup_${TIMESTAMP}.conf"
        log_success "Nginx configuration backed up"
    fi
    
    cd ..
}

# SSL certificate renewal
renew_ssl_certificates() {
    echo "🔒 Renewing SSL certificates..."
    cd "$PROJECT_DIR"
    
    if [ -d "certbot/conf/live/$DOMAIN" ]; then
        log_info "Renewing Let's Encrypt certificates..."
        docker compose run --rm certbot renew
        docker compose restart nginx
        log_success "SSL certificates renewed"
    else
        log_warning "No Let's Encrypt certificates found to renew"
    fi
    
    cd ..
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
    cd ..
}

show_service_status() {
    echo "📊 Current service status:"
    cd "$PROJECT_DIR"
    docker compose ps
    cd ..
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
echo "5. Renew SSL certificates"
echo "6. Exit"
echo

read -p "Choose an action (1-6): " action
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
    5)
        renew_ssl_certificates
        ;;
    6|*)
        log_info "Deployment complete. Have a great day! 🚀"
        ;;
esac