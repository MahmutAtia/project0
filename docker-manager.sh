#!/bin/bash

# Docker Manager Script for CareerFlow Project
# Usage: ./docker-manager.sh [environment] [action] [services...]
# Example: ./docker-manager.sh dev up api django

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    echo "Docker Manager for CareerFlow Project"
    echo ""
    echo "Usage: $0 [environment] [action] [services...]"
    echo ""
    echo "Environments:"
    echo "  dev     - Development environment (with hot reload)"
    echo "  prod    - Production environment (with nginx, ssl)"
    echo ""
    echo "Actions:"
    echo "  up      - Start services"
    echo "  down    - Stop services"
    echo "  restart - Restart services"
    echo "  logs    - Show logs"
    echo "  build   - Build images"
    echo "  pull    - Pull latest images"
    echo "  ps      - Show running containers"
    echo "  exec    - Execute command in container"
    echo ""
    echo "Services (optional - if not specified, all services will be affected):"
    echo "  api        - FastAPI service"
    echo "  django     - Django backend"
    echo "  careerflow - Next.js frontend"
    echo "  db         - PostgreSQL database"
    echo "  redis      - Redis cache"
    echo "  celery     - Celery worker"
    echo "  nginx      - Nginx proxy (prod only)"
    echo "  certbot    - SSL certificates (prod only)"
    echo ""
    echo "Examples:"
    echo "  $0 dev up                    # Start all dev services"
    echo "  $0 dev up api django         # Start only api and django in dev"
    echo "  $0 prod up                   # Start all production services"
    echo "  $0 dev logs api              # Show api logs in dev"
    echo "  $0 dev exec django bash      # Execute bash in django container"
    echo "  $0 dev down                  # Stop all dev services"
    echo ""
}

# Check if docker compose is available
check_docker_compose() {
    if command -v docker &> /dev/null; then
        if docker compose version &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker compose"
            return 0
        elif command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker-compose"
            return 0
        else
            print_error "Docker Compose not found. Please install Docker Compose."
            exit 1
        fi
    else
        print_error "Docker not found. Please install Docker."
        exit 1
    fi
}

# Validate environment
validate_environment() {
    if [ "$1" != "dev" ] && [ "$1" != "prod" ]; then
        print_error "Invalid environment: $1"
        print_info "Valid environments: dev, prod"
        exit 1
    fi
}

# Validate action
validate_action() {
    case $1 in
        up|down|restart|logs|build|pull|ps|exec)
            return 0
            ;;
        *)
            print_error "Invalid action: $1"
            print_info "Valid actions: up, down, restart, logs, build, pull, ps, exec"
            exit 1
            ;;
    esac
}

# Main script logic
main() {
    # Check arguments
    if [ $# -lt 2 ]; then
        show_help
        exit 1
    fi

    # Check docker compose availability
    check_docker_compose
    print_info "Using: $DOCKER_COMPOSE_CMD"

    # Parse arguments
    ENVIRONMENT=$1
    ACTION=$2
    shift 2
    SERVICES="$*"

    # Validate inputs
    validate_environment "$ENVIRONMENT"
    validate_action "$ACTION"

    # Set compose file and env file based on environment
    if [ "$ENVIRONMENT" = "dev" ]; then
        COMPOSE_FILE="docker-compose.dev.yml"
        ENV_FILE=".env.dev"
    else
        COMPOSE_FILE="docker-compose.yml"
        ENV_FILE=".env"
    fi

    # Check if files exist
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        print_info "Please create $ENV_FILE based on .env.example"
        exit 1
    fi

    # Base docker-compose command
    DOCKER_CMD="$DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE"

    # Function to execute docker-compose commands
    execute_docker_cmd() {
        local cmd="$1"
        print_info "Executing: $cmd"
        eval "$cmd"
    }

    # Handle different actions
    case $ACTION in
        "up")
            if [ "$ENVIRONMENT" = "prod" ] && [ -z "$SERVICES" ]; then
                print_info "Starting production environment..."
                execute_docker_cmd "$DOCKER_CMD up -d $SERVICES"
            else
                print_info "Starting $ENVIRONMENT environment..."
                execute_docker_cmd "$DOCKER_CMD up -d $SERVICES"
            fi
            print_success "Services started successfully!"
            ;;
        "down")
            print_info "Stopping $ENVIRONMENT environment..."
            execute_docker_cmd "$DOCKER_CMD down $SERVICES"
            print_success "Services stopped successfully!"
            ;;
        "restart")
            print_info "Restarting $ENVIRONMENT services..."
            execute_docker_cmd "$DOCKER_CMD restart $SERVICES"
            print_success "Services restarted successfully!"
            ;;
        "logs")
            if [ -z "$SERVICES" ]; then
                print_info "Showing logs for all services..."
                execute_docker_cmd "$DOCKER_CMD logs -f"
            else
                print_info "Showing logs for: $SERVICES"
                execute_docker_cmd "$DOCKER_CMD logs -f $SERVICES"
            fi
            ;;
        "build")
            if [ -z "$SERVICES" ]; then
                print_info "Building all images..."
                execute_docker_cmd "$DOCKER_CMD build"
            else
                print_info "Building images for: $SERVICES"
                execute_docker_cmd "$DOCKER_CMD build $SERVICES"
            fi
            print_success "Build completed successfully!"
            ;;
        "pull")
            print_info "Pulling latest images..."
            execute_docker_cmd "$DOCKER_CMD pull $SERVICES"
            print_success "Images pulled successfully!"
            ;;
        "ps")
            print_info "Showing running containers..."
            execute_docker_cmd "$DOCKER_CMD ps"
            ;;
        "exec")
            if [ -z "$SERVICES" ]; then
                print_error "Service name required for exec command"
                print_info "Usage: $0 $ENVIRONMENT exec [service] [command]"
                exit 1
            fi
            
            SERVICE=$(echo $SERVICES | cut -d' ' -f1)
            COMMAND=$(echo $SERVICES | cut -d' ' -f2-)
            
            if [ "$SERVICE" = "$COMMAND" ]; then
                COMMAND="bash"
            fi
            
            print_info "Executing '$COMMAND' in $SERVICE container..."
            execute_docker_cmd "$DOCKER_CMD exec -it $SERVICE $COMMAND"
            ;;
    esac
}

# Run main function
main "$@"