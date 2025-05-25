#!/bin/bash

# Deployment Script for CareerFlow (Handling Separate Frontend Repo with SSL)

# --- Configuration ---
# Main Backend Repository (contains docker compose.yml, django, api, etc.)
BACKEND_GIT_REPO_URL="https://github.com/MahmutAtia/project0.git"
BACKEND_PROJECT_DIR_NAME="./" # Backend will be cloned to the same directory as deploy.sh
BACKEND_BRANCH="prod" # Set backend branch to prod

# Frontend Repository (CareerFlow Next.js app)
FRONTEND_GIT_REPO_URL="https://github.com/MahmutAtia/proj0_front.git"
FRONTEND_PROJECT_DIR_NAME="careerflow" # Frontend will be cloned to ./careerflow
FRONTEND_BRANCH="prod" # Set frontend branch to prod
# This is the name of the subdirectory INSIDE BACKEND_PROJECT_DIR_NAME where the frontend will be cloned.
# It MUST match the 'context' path in docker compose.yml for the careerflow service (e.g., "careerflow" if context is "./careerflow")
FRONTEND_SUBDIR_NAME="careerflow" # Should be consistent with FRONTEND_PROJECT_DIR_NAME if cloned as a subdir

ENV_FILE=".env" # This .env file will be in the root  of BACKEND_PROJECT_DIR_NAME
DOCKER_COMPOSE_FILE="docker-compose.yml"

# --- Self-preservation logic ---
SCRIPT_EXECUTING_PATH=$(readlink -f "$0")
SCRIPT_EXECUTING_NAME=$(basename "$SCRIPT_EXECUTING_PATH")
SCRIPT_EXECUTING_DIR=$(dirname "$SCRIPT_EXECUTING_PATH")
TEMP_SCRIPT_COPY=""

# Check if the script is running from the directory designated as BACKEND_PROJECT_DIR_NAME
# and if BACKEND_PROJECT_DIR_NAME is set to "./" (current directory)
# This means the script is in the root of the backend project.
if [ "$(realpath "$SCRIPT_EXECUTING_DIR")" = "$(realpath "$PWD/$BACKEND_PROJECT_DIR_NAME")" ]; then
  TEMP_SCRIPT_COPY="/tmp/${SCRIPT_EXECUTING_NAME}.$$_deploy_backup"
  cp "$SCRIPT_EXECUTING_PATH" "$TEMP_SCRIPT_COPY"
  # Ensure cleanup on exit or interruption
  trap 'if [ -n "$TEMP_SCRIPT_COPY" ] && [ -f "$TEMP_SCRIPT_COPY" ]; then rm -f "$TEMP_SCRIPT_COPY"; fi' EXIT HUP INT QUIT TERM
fi

# --- Helper Functions ---
print_success() {
  echo -e "\033[0;32mSUCCESS: $1\033[0m"
}
print_error() {
  echo -e "\033[0;31mERROR: $1\033[0m" >&2
}
print_warning() {
  echo -e "\033[0;33mWARNING: $1\033[0m"
}
print_info() {
  echo -e "\033[0;34mINFO: $1\033[0m"
}
check_command() {
  local cmd="$1"
  if ! command -v "$cmd" &> /dev/null; then
    print_error "$cmd could not be found. Please install it and try again."
    exit 1
  fi
}
update_env_var() {
  local var_name="$1"
  local var_value="$2"
  local env_file_path="$3"
  local escaped_var_value=$(sed 's/[&/\]/\\&/g' <<< "$var_value")
  if grep -q "^${var_name}=" "$env_file_path"; then
    sed -i "s|^${var_name}=.*|${var_name}=${escaped_var_value}|" "$env_file_path"
    print_info "Updated ${var_name} in ${env_file_path}."
  else
    echo "${var_name}=${escaped_var_value}" >> "$env_file_path"
    print_info "Added ${var_name}=${escaped_var_value} to ${env_file_path}."
  fi
}

# --- SSL Setup Functions ---
setup_ssl() {
    local domain=$1
    local email=$2
    
    print_info "Setting up SSL certificates for domain: $domain"
    
    if [ "$domain" = "localhost" ]; then
        # Create self-signed certificates for localhost
        print_info "Creating self-signed certificates for localhost..."
        mkdir -p nginx/ssl
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/localhost.key \
            -out nginx/ssl/localhost.crt \
            -subj "/C=US/ST=Test/L=Test/O=Test/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null || \
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/localhost.key \
            -out nginx/ssl/localhost.crt \
            -subj "/C=US/ST=Test/L=Test/O=Test/CN=localhost"
            
        print_success "Self-signed certificates created for localhost"
        
    else
        # Try to get Let's Encrypt certificates
        print_info "Attempting to get Let's Encrypt certificate for $domain..."
        
        # Start nginx first for webroot validation
        print_info "Starting nginx for certificate validation..."
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d nginx
        sleep 10
        
        # Check if domain is accessible
        print_info "Checking domain accessibility..."
        if curl -s --connect-timeout 10 "http://$domain:880/.well-known/acme-challenge/" > /dev/null 2>&1; then
            print_info "Domain appears to be accessible, proceeding with Let's Encrypt..."
            
            # Try to get certificate without profile flag (for older docker-compose versions)
            if docker compose -f "$DOCKER_COMPOSE_FILE" run --rm certbot certonly \
                --webroot \
                --webroot-path=/var/www/certbot \
                --email "$email" \
                --agree-tos \
                --no-eff-email \
                --non-interactive \
                -d "$domain"; then
                
                print_success "Let's Encrypt certificate obtained for $domain"
                
                # Copy certificates to nginx ssl directory for easier access
                mkdir -p nginx/ssl
                docker run --rm \
                    -v "$(pwd)/nginx/ssl:/ssl" \
                    -v "$(docker compose -f "$DOCKER_COMPOSE_FILE" config --volumes | grep certbot-etc):$(docker compose -f "$DOCKER_COMPOSE_FILE" config --volumes | grep certbot-etc)" \
                    alpine:latest sh -c "
                        if [ -f /etc/letsencrypt/live/$domain/fullchain.pem ]; then
                            cp /etc/letsencrypt/live/$domain/fullchain.pem /ssl/$domain.crt 2>/dev/null || true
                            cp /etc/letsencrypt/live/$domain/privkey.pem /ssl/$domain.key 2>/dev/null || true
                            echo 'Certificates copied successfully'
                        else
                            echo 'Let's Encrypt certificates not found'
                            exit 1
                        fi
                    " 2>/dev/null
                
                if [ $? -eq 0 ]; then
                    print_success "Let's Encrypt certificates copied to nginx/ssl/"
                    return 0
                fi
            fi
        else
            print_warning "Domain $domain is not accessible from the internet. This is required for Let's Encrypt validation."
        fi
        
        # Fallback to self-signed certificate
        print_warning "Failed to get Let's Encrypt certificate. Creating self-signed certificate as fallback..."
        mkdir -p nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "nginx/ssl/$domain.key" \
            -out "nginx/ssl/$domain.crt" \
            -subj "/C=US/ST=Test/L=Test/O=Test/CN=$domain"
        print_info "Self-signed certificate created for $domain"
    fi
}

setup_nginx_config() {
    local domain=$1
    
    print_info "Configuring nginx for domain: $domain"
    
    # If template exists, use it with envsubst
    if [ -f "nginx/conf.d/default.conf.template" ]; then
        envsubst '${DOMAIN}' < nginx/conf.d/default.conf.template > nginx/conf.d/default.conf
        print_success "Nginx configuration created from template"
    else
        # Update existing config with domain
        if [ -f "nginx/conf.d/default.conf" ]; then
            sed -i "s/server_name localhost.*/server_name $domain;/g" nginx/conf.d/default.conf
            sed -i "s|ssl_certificate /etc/nginx/ssl/.*\.crt;|ssl_certificate /etc/nginx/ssl/$domain.crt;|g" nginx/conf.d/default.conf
            sed -i "s|ssl_certificate_key /etc/nginx/ssl/.*\.key;|ssl_certificate_key /etc/nginx/ssl/$domain.key;|g" nginx/conf.d/default.conf
            print_success "Nginx configuration updated"
        fi
    fi
}

detect_environment() {
    # Simple environment detection
    if [ -n "$SERVER_MODE" ] || [ -n "$CI" ] || [[ "$(hostname)" != *"localhost"* && "$(hostname)" != *"127.0.0.1"* ]]; then
        echo "server"
    else
        echo "localhost"
    fi
}

# --- Main Deployment Logic ---

print_info "🚀 Starting CareerFlow deployment with SSL automation..."

# 1. Check for necessary tools
print_info "Checking for required tools (git, docker, docker compose, openssl)..."
check_command "git"
check_command "docker"
check_command "openssl"
print_success "All required tools are installed."

# 2. Clone or update Backend Repository
if [ -f "$DOCKER_COMPOSE_FILE" ]; then
  print_info "Backend project already exists (found $DOCKER_COMPOSE_FILE). Updating..."
  if [ ! -d ".git" ]; then
    print_error ".git directory not found, but $DOCKER_COMPOSE_FILE exists. This script expects to manage the backend git repo. Please check your setup or remove $DOCKER_COMPOSE_FILE to re-initialize."
    exit 1
  fi
  
  current_remote_url=$(git config --get remote.origin.url)
  if [ "$current_remote_url" != "$BACKEND_GIT_REPO_URL" ]; then
      print_warning "Backend remote 'origin' URL mismatch. Current: $current_remote_url, Expected: $BACKEND_GIT_REPO_URL. Updating remote."
      git remote set-url origin "$BACKEND_GIT_REPO_URL"
      if [ $? -ne 0 ]; then print_error "Failed to set backend remote origin URL."; exit 1; fi
  fi

  print_info "Fetching latest changes for backend branch '$BACKEND_BRANCH'..."
  git fetch --depth 1 origin "+$BACKEND_BRANCH:refs/remotes/origin/$BACKEND_BRANCH"
   if [ $? -ne 0 ]; then
    print_warning "Shallow fetch for backend branch '$BACKEND_BRANCH' failed, attempting full fetch..."
    git fetch origin "+$BACKEND_BRANCH:refs/remotes/origin/$BACKEND_BRANCH"
    if [ $? -ne 0 ]; then print_error "Failed to fetch origin for backend branch '$BACKEND_BRANCH'."; exit 1; fi
  fi

  print_info "Checking out and resetting backend branch '$BACKEND_BRANCH' to 'origin/$BACKEND_BRANCH'..."
  git checkout -f -B "$BACKEND_BRANCH" "refs/remotes/origin/$BACKEND_BRANCH"
  if [ $? -ne 0 ]; then print_error "Failed to checkout/reset backend branch '$BACKEND_BRANCH' to 'origin/$BACKEND_BRANCH'."; exit 1; fi
  
  git reset --hard "refs/remotes/origin/$BACKEND_BRANCH"
  if [ $? -ne 0 ]; then
    print_error "Failed to reset backend branch to 'origin/$BACKEND_BRANCH'."
    exit 1
  fi

  # Restore the original running script if it was backed up
  if [ -n "$TEMP_SCRIPT_COPY" ] && [ -f "$TEMP_SCRIPT_COPY" ]; then
    cp "$TEMP_SCRIPT_COPY" "./$SCRIPT_EXECUTING_NAME"
    chmod +x "./$SCRIPT_EXECUTING_NAME"
  elif [ -f "./$SCRIPT_EXECUTING_NAME" ]; then
     chmod +x "./$SCRIPT_EXECUTING_NAME"
  fi
  print_success "Backend updated successfully."
else
  print_info "Backend project files (e.g., $DOCKER_COMPOSE_FILE) not found. Setting up repository in current directory ('$BACKEND_PROJECT_DIR_NAME')..."
  
  if [ ! -d ".git" ]; then
    print_info "Initializing new Git repository in current directory..."
    if git init -b "$BACKEND_BRANCH" 2>/dev/null; then
        print_info "Initialized git with default branch $BACKEND_BRANCH."
    else
        git init
        print_info "Initialized git. Will checkout $BACKEND_BRANCH."
    fi
    if [ $? -ne 0 ]; then print_error "Failed to initialize git repository."; exit 1; fi

    git remote add origin "$BACKEND_GIT_REPO_URL"
    if [ $? -ne 0 ]; then print_error "Failed to add remote origin '$BACKEND_GIT_REPO_URL'."; exit 1; fi
  else
    print_info "Existing .git directory found. Ensuring remote 'origin' is correct for backend."
    if git remote | grep -q '^origin$'; then
        current_remote_url=$(git config --get remote.origin.url)
        if [ "$current_remote_url" != "$BACKEND_GIT_REPO_URL" ]; then
            print_warning "Backend remote 'origin' URL mismatch. Current: $current_remote_url, Expected: $BACKEND_GIT_REPO_URL. Updating remote."
            git remote set-url origin "$BACKEND_GIT_REPO_URL"
            if [ $? -ne 0 ]; then print_error "Failed to set backend remote origin URL."; exit 1; fi
        fi
    else
        print_info "Remote 'origin' not found for backend. Adding remote 'origin' $BACKEND_GIT_REPO_URL"
        git remote add origin "$BACKEND_GIT_REPO_URL"
        if [ $? -ne 0 ]; then print_error "Failed to add remote origin '$BACKEND_GIT_REPO_URL'."; exit 1; fi
    fi
  fi

  print_info "Fetching backend branch '$BACKEND_BRANCH' from $BACKEND_GIT_REPO_URL..."
  git fetch --depth 1 origin "+$BACKEND_BRANCH:refs/remotes/origin/$BACKEND_BRANCH"
  if [ $? -ne 0 ]; then
    print_warning "Shallow fetch failed for backend, attempting full fetch for branch '$BACKEND_BRANCH'..."
    git fetch origin "+$BACKEND_BRANCH:refs/remotes/origin/$BACKEND_BRANCH"
    if [ $? -ne 0 ]; then print_error "Full fetch also failed for backend branch '$BACKEND_BRANCH'."; exit 1; fi
  fi

  print_info "Checking out and resetting backend to 'origin/$BACKEND_BRANCH'..."
  git checkout -f -B "$BACKEND_BRANCH" "refs/remotes/origin/$BACKEND_BRANCH"
  if [ $? -ne 0 ]; then print_error "Failed to checkout/reset backend local branch '$BACKEND_BRANCH' to 'origin/$BACKEND_BRANCH'."; exit 1; fi
  
  git reset --hard "refs/remotes/origin/$BACKEND_BRANCH"
  if [ $? -ne 0 ]; then print_error "Failed to hard reset backend local branch '$BACKEND_BRANCH' to 'origin/$BACKEND_BRANCH'."; exit 1; fi

  # Restore the original running script if it was backed up
  if [ -n "$TEMP_SCRIPT_COPY" ] && [ -f "$TEMP_SCRIPT_COPY" ]; then
    cp "$TEMP_SCRIPT_COPY" "./$SCRIPT_EXECUTING_NAME"
    chmod +x "./$SCRIPT_EXECUTING_NAME"
  elif [ -f "./$SCRIPT_EXECUTING_NAME" ]; then
    chmod +x "./$SCRIPT_EXECUTING_NAME"
  fi
  print_success "Backend repository set up successfully in current directory."
fi

# 3. Clone or update Frontend Repository
FRONTEND_FULL_PATH="${BACKEND_PROJECT_DIR_NAME%/}/${FRONTEND_PROJECT_DIR_NAME}"
NEEDS_CLONE=false

if [ -d "$FRONTEND_FULL_PATH" ]; then
  print_info "Frontend project directory '$FRONTEND_FULL_PATH' already exists. Checking status..."
  if [ -d "${FRONTEND_FULL_PATH}/.git" ]; then
    print_info "Found .git directory in '$FRONTEND_FULL_PATH'. Attempting update..."
    ( 
      cd "$FRONTEND_FULL_PATH" || { print_error "Could not cd to '$FRONTEND_FULL_PATH'."; exit 1; }

      current_frontend_remote_url=$(git config --get remote.origin.url)
      if [ "$current_frontend_remote_url" != "$FRONTEND_GIT_REPO_URL" ]; then
          print_warning "Frontend remote 'origin' URL mismatch. Current: '$current_frontend_remote_url', Expected: '$FRONTEND_GIT_REPO_URL'. Updating remote."
          git remote set-url origin "$FRONTEND_GIT_REPO_URL"
          if [ $? -ne 0 ]; then print_error "Failed to set frontend remote origin URL."; exit 1; fi
      fi

      print_info "Fetching latest for frontend branch '$FRONTEND_BRANCH' from remote 'origin'..."
      git fetch --depth 1 origin "+$FRONTEND_BRANCH:refs/remotes/origin/$FRONTEND_BRANCH"
      if [ $? -ne 0 ]; then
          print_warning "Shallow fetch for frontend branch '$FRONTEND_BRANCH' failed, attempting full fetch..."
          git fetch origin "+$FRONTEND_BRANCH:refs/remotes/origin/$FRONTEND_BRANCH"
          if [ $? -ne 0 ]; then print_error "Failed to fetch origin for frontend branch '$FRONTEND_BRANCH'."; exit 1; fi
      fi

      print_info "Checking out and resetting frontend branch '$FRONTEND_BRANCH' to 'origin/$FRONTEND_BRANCH'..."
      git checkout -f -B "$FRONTEND_BRANCH" "refs/remotes/origin/$FRONTEND_BRANCH"
      if [ $? -ne 0 ]; then print_error "Failed to checkout/reset frontend branch '$FRONTEND_BRANCH' to 'origin/$FRONTEND_BRANCH'."; exit 1; fi
      
      git reset --hard "refs/remotes/origin/$FRONTEND_BRANCH"
      if [ $? -ne 0 ]; then
        print_error "Failed to hard reset frontend branch '$FRONTEND_BRANCH'."
        exit 1
      fi
      print_success "Frontend updated successfully."
    )
    subshell_exit_status=$?
    if [ $subshell_exit_status -ne 0 ]; then
        print_error "Frontend update process failed. Exiting script."
        exit 1
    fi
  else
    print_warning "Directory '$FRONTEND_FULL_PATH' exists but does not contain a .git directory. Removing and re-cloning."
    rm -rf "$FRONTEND_FULL_PATH"
    if [ $? -ne 0 ]; then
        print_error "Failed to remove existing problematic directory '$FRONTEND_FULL_PATH'. Please remove it manually and re-run."
        exit 1
    fi
    NEEDS_CLONE=true
  fi
else
  NEEDS_CLONE=true
fi

if [ "$NEEDS_CLONE" = true ]; then
  print_info "Cloning frontend repository from $FRONTEND_GIT_REPO_URL (branch: $FRONTEND_BRANCH) into $FRONTEND_FULL_PATH..."
  git clone --branch "$FRONTEND_BRANCH" --single-branch --depth 1 "$FRONTEND_GIT_REPO_URL" "$FRONTEND_FULL_PATH"
  if [ $? -ne 0 ]; then
    print_error "Failed to clone frontend repository into $FRONTEND_FULL_PATH."
    exit 1
  fi
  print_success "Frontend repository cloned successfully into $FRONTEND_FULL_PATH."
fi

# 4. Environment Detection and Configuration
ENV_TYPE=$(detect_environment)
print_info "Environment detected: $ENV_TYPE"

if [ -f "$ENV_FILE" ]; then
  print_info ".env file already exists. Ensuring production settings are applied."
else
  print_info "Creating .env file..."
  touch "$ENV_FILE"
  print_warning "A new .env file has been created. Please ensure all necessary production variables are set."
fi

print_info "Configuring environment variables for $ENV_TYPE environment..."

if [ "$ENV_TYPE" = "server" ]; then
    # Server mode
    if [ -z "$DOMAIN" ]; then
        read -rp "Enter your domain name (e.g., srv658540.hstgr.cloud): " DOMAIN
    fi
    if [ -z "$CERTBOT_EMAIL" ]; then
        read -rp "Enter email for SSL certificates: " CERTBOT_EMAIL
    fi
    
    update_env_var "DOMAIN" "$DOMAIN" "$ENV_FILE"
    update_env_var "CERTBOT_EMAIL" "$CERTBOT_EMAIL" "$ENV_FILE"
    
    # Use HTTPS URLs for production
    update_env_var "NEXT_PUBLIC_BACKEND_URL" "https://${DOMAIN}:8443" "$ENV_FILE"
    update_env_var "NEXT_PUBLIC_API_URL" "https://${DOMAIN}:8443/api" "$ENV_FILE"
    update_env_var "NEXT_PUBLIC_AI_API_URL" "https://${DOMAIN}:8443/ai-api" "$ENV_FILE"
    update_env_var "NEXTAUTH_URL" "https://${DOMAIN}:8443" "$ENV_FILE"
    update_env_var "NEXTAUTH_BACKEND_URL" "https://${DOMAIN}:8443" "$ENV_FILE"
    
    print_info "Server mode configured for domain: $DOMAIN"
    
else
    # Localhost mode
    DOMAIN="localhost"
    CERTBOT_EMAIL="admin@localhost"
    
    update_env_var "DOMAIN" "$DOMAIN" "$ENV_FILE"
    update_env_var "CERTBOT_EMAIL" "$CERTBOT_EMAIL" "$ENV_FILE"
    
    # Use HTTP URLs for localhost (port 880)
    update_env_var "NEXT_PUBLIC_BACKEND_URL" "http://localhost:880" "$ENV_FILE"
    update_env_var "NEXT_PUBLIC_API_URL" "http://localhost:880/api" "$ENV_FILE"
    update_env_var "NEXT_PUBLIC_AI_API_URL" "http://localhost:880/ai-api" "$ENV_FILE"
    update_env_var "NEXTAUTH_URL" "http://localhost:880" "$ENV_FILE"
    update_env_var "NEXTAUTH_BACKEND_URL" "http://localhost:880" "$ENV_FILE"
    
    print_info "Localhost mode configured - using HTTP on port 880"
fi

# Set common variables
update_env_var "NODE_ENV" "production" "$ENV_FILE"
update_env_var "DEBUG" "0" "$ENV_FILE"
update_env_var "PYTHONUNBUFFERED" "1" "$ENV_FILE"

# Critical variables validation
critical_vars=(
  "DJANGO_SECRET_KEY" "POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB"
  "NEXTAUTH_SECRET" "GOOGLE_CLIENT_ID" "GOOGLE_CLIENT_SECRET"
  "GOOGLE_API_KEY" "LANGCHAIN_API_KEY" "EMAIL_HOST_PASSWORD"
)

print_info "Checking critical environment variables..."
for var in "${critical_vars[@]}"; do
  if ! grep -q "^${var}=" "$ENV_FILE"; then
    read -rp "Enter value for ${var}: " value
    if [ -z "$value" ]; then
        print_error "${var} cannot be empty. Deployment aborted."
        exit 1
    fi
    update_env_var "${var}" "${value}" "$ENV_FILE"
  fi
done

# 5. Setup SSL and Nginx
setup_nginx_config "$DOMAIN"
setup_ssl "$DOMAIN" "$CERTBOT_EMAIL"

# 6. Build Docker images
print_info "Building Docker images (this may take some time)..."
docker compose -f "$DOCKER_COMPOSE_FILE" build
if [ $? -ne 0 ]; then 
    print_error "Docker build failed."
    exit 1
fi
print_success "Docker images built successfully."

# 7. Database setup
print_info "Ensuring database service is up for migrations..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d db
print_info "Waiting for database to initialize (15 seconds)..."
sleep 15

print_info "Running Django makemigrations..."
docker compose -f "$DOCKER_COMPOSE_FILE" run --rm django python manage.py makemigrations
if [ $? -ne 0 ]; then
  print_warning "Django makemigrations command finished with non-zero status. This might be okay if there are no new model changes."
fi

print_info "Running Django migrate..."
docker compose -f "$DOCKER_COMPOSE_FILE" run --rm django python manage.py migrate
if [ $? -ne 0 ]; then print_error "Django migrate failed."; exit 1; fi
print_success "Django migrations completed successfully."

# 8. Start all services
print_info "Starting all services..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d
if [ $? -ne 0 ]; then print_error "Failed to start services with docker compose."; exit 1; fi

# 9. Setup auto-renewal for production (simplified without profile)
if [ "$DOMAIN" != "localhost" ]; then
    print_info "Setting up automatic SSL renewal..."
    (crontab -l 2>/dev/null; echo "0 2 * * * cd $(pwd) && docker compose run --rm certbot renew --quiet && docker compose restart nginx") | crontab -
    print_success "SSL auto-renewal configured (runs daily at 2 AM)"
fi

# 10. Final status
print_success "🎉 Deployment completed successfully!"
print_info "Your application is accessible at:"
if [ "$DOMAIN" = "localhost" ]; then
    print_info "  📱 HTTP:  http://localhost:880"
    print_info "  🔒 HTTPS: https://localhost:8443 (accept certificate warning)"
else
    print_info "  📱 HTTP:  http://$DOMAIN:880"
    print_info "  🔒 HTTPS: https://$DOMAIN:8443"
fi

print_info "Service status:"
docker compose -f "$DOCKER_COMPOSE_FILE" ps