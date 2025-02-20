#!/bin/bash

set -e

# Configuration
ENV=${1:-production}
VERSION=$(git describe --tags --always)
DOCKER_REGISTRY="your-registry.com"

# Logging setup
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

# Deployment steps
check_prerequisites() {
    command -v docker >/dev/null 2>&1 || error "Docker is required"
    command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is required"
}

deploy() {
    log "Starting deployment for environment: $ENV"
    
    # Build and push Docker image
    log "Building Docker image..."
    docker build -t $DOCKER_REGISTRY/mev-bot:$VERSION .
    docker push $DOCKER_REGISTRY/mev-bot:$VERSION
    
    # Run database migrations
    log "Running database migrations..."
    alembic upgrade head
    
    # Deploy application
    log "Deploying application..."
    docker-compose -f docker-compose.yml -f docker-compose.$ENV.yml up -d
    
    # Verify deployment
    log "Verifying deployment..."
    sleep 10
    curl -f http://localhost:8000/health || error "Health check failed"
    
    log "Deployment completed successfully"
}

check_prerequisites
deploy

