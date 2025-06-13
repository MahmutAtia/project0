#!/bin/bash

# Simple Deployment Script for CareerFlow
# Run this script from outside the project directory

# Exit on any error
set -e

# --- Configuration ---
BACKEND_REPO="https://github.com/MahmutAtia/project0.git"
FRONTEND_REPO="https://github.com/MahmutAtia/proj0_front.git"
PROJECT_DIR="prod"
FRONTEND_DIR="careerflow"
BRANCH="prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if command exists
check_tool() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed"
        exit 1
    fi
}

# Main deployment function
main() {
    log_info "Starting CareerFlow deployment..."
    log_info "Working directory: $(pwd)"
    
    # Check required tools
    log_info "Checking required tools..."
    check_tool git
    check_tool docker
    log_success "All tools are available"
    
    # Handle backend repository
    log_info "Managing backend repository..."
    if [ -d "$PROJECT_DIR" ]; then
        log_info "Updating existing backend..."
        cd "$PROJECT_DIR"
        
        # Force update to match remote
        git fetch origin $BRANCH
        git reset --hard origin/$BRANCH
        
        cd ..
        log_success "Backend updated"
    else
        log_info "Cloning backend repository..."
        git clone -b $BRANCH $BACKEND_REPO $PROJECT_DIR
        log_success "Backend cloned"
    fi
    
    # Handle frontend repository
    log_info "Managing frontend repository..."
    FRONTEND_PATH="$PROJECT_DIR/$FRONTEND_DIR"
    
    if [ -d "$FRONTEND_PATH" ]; then
        log_info "Updating existing frontend..."
        cd "$FRONTEND_PATH"
        
        # Force update to match remote
        git fetch origin $BRANCH
        git reset --hard origin/$BRANCH
        
        cd ../..
        log_success "Frontend updated"
    else
        log_info "Cloning frontend repository..."
        cd "$PROJECT_DIR"
        git clone -b $BRANCH $FRONTEND_REPO $FRONTEND_DIR
        cd ..
        log_success "Frontend cloned"
    fi
    
    # Setup environment file
    log_info "Setting up environment..."
    ENV_FILE="$PROJECT_DIR/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        log_info "Creating .env file..."
        cat > "$ENV_FILE" << EOF
# Production Environment
NODE_ENV=production
DEBUG=0
PYTHONUNBUFFERED=1

# Database
POSTGRES_DB=careerflow_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_db_password

# Django
DJANGO_SECRET_KEY=your_secret_key_here
DJANGO_ALLOWED_HOSTS=*

# Auth
NEXTAUTH_SECRET=your_nextauth_secret
NEXTAUTH_URL=http://localhost:3000

# Google
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_API_KEY=your_google_api_key

# Other APIs
LANGCHAIN_API_KEY=your_langchain_key
EMAIL_HOST_PASSWORD=your_email_password
JWT_SECRET_KEY=your_jwt_secret
EOF
        log_warning "Please edit $ENV_FILE with your actual values"
        read -p "Press Enter after editing the .env file..."
    else
        log_info ".env file already exists"
    fi
    

    # Generate SSL certificates if they don't exist
    log_info "Setting up SSL certificates..."
    if [ ! -f "$PROJECT_DIR/nginx/ssl/localhost.crt" ]; then
        log_info "Generating self-signed SSL certificates..."
        cd "$PROJECT_DIR"
        mkdir -p nginx/ssl
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
          -keyout nginx/ssl/localhost.key \
          -out nginx/ssl/localhost.crt \
          -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=srv658540.hstgr.cloud" \
          -addext "subjectAltName=DNS:srv658540.hstgr.cloud,DNS:localhost" 2>/dev/null || {
          # Fallback for older OpenSSL versions
          log_warning "Using fallback SSL generation for older OpenSSL..."
          openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/localhost.key \
            -out nginx/ssl/localhost.crt \
            -subj "/C=US/ST=State/L=City/O=CareerFlow/CN=srv658540.hstgr.cloud"
        }
        
        cd ..
        log_success "SSL certificates generated"
    else
        log_info "SSL certificates already exist"  
    fi
    # Build and start services
    log_info "Building Docker images..."
    cd "$PROJECT_DIR"
    docker compose build
    log_success "Images built"
    
    log_info "Starting database..."
    docker compose up -d db
    sleep 10
    
    log_info "Running migrations..."
    docker compose run --rm django python manage.py migrate
    log_success "Migrations completed"
    
    log_info "Starting all services..."
    docker compose up -d
    log_success "All services started"
    
    cd ..
    
    # Show status
    log_success "Deployment completed!"
    log_info "Services status:"
    cd "$PROJECT_DIR"
    docker compose ps
    cd ..
    
    log_info "Application should be available at:"
    log_info "- Frontend: http://localhost:3000"
    log_info "- Backend API: http://localhost:8000"
    log_info "- Nginx: http://localhost:880"
}

# Run main function
main