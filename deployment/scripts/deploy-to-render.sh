#!/bin/bash

# MAGSASA-CARD Platform - Render Deployment Script
# Automates deployment to Render staging environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="MAGSASA-CARD Platform"
ENVIRONMENT="staging"
RENDER_CONFIG="deployment/render/render.yaml"
DEPLOYMENT_STATE="deployment/deployment-state.json"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [ ! -f "app_production.py" ]; then
        log_error "app_production.py not found. Please run this script from the project root."
        exit 1
    fi
    
    # Check if render.yaml exists
    if [ ! -f "$RENDER_CONFIG" ]; then
        log_error "Render configuration file not found: $RENDER_CONFIG"
        exit 1
    fi
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed."
        exit 1
    fi
    
    # Check if we're in a git repository
    if [ ! -d ".git" ]; then
        log_error "Not in a git repository. Please initialize git first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

validate_configuration() {
    log_info "Validating configuration files..."
    
    # Check if production requirements exist
    if [ ! -f "requirements_production.txt" ]; then
        log_error "requirements_production.txt not found"
        exit 1
    fi
    
    # Check if environment config exists
    if [ ! -f "deployment/configs/.env.staging" ]; then
        log_warning "Staging environment config not found, using defaults"
    fi
    
    # Validate render.yaml syntax (basic check)
    if ! grep -q "services:" "$RENDER_CONFIG"; then
        log_error "Invalid render.yaml format"
        exit 1
    fi
    
    log_success "Configuration validation passed"
}

prepare_deployment() {
    log_info "Preparing deployment..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Update deployment timestamp in state file
    if [ -f "$DEPLOYMENT_STATE" ]; then
        TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        # Update the deployment state (simplified - in production use jq)
        log_info "Updating deployment timestamp: $TIMESTAMP"
    fi
    
    # Ensure all necessary directories exist
    mkdir -p src/database
    
    log_success "Deployment preparation completed"
}

check_git_status() {
    log_info "Checking git status..."
    
    # Check if there are uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "There are uncommitted changes in the repository"
        echo "Uncommitted files:"
        git status --porcelain
        
        read -p "Do you want to commit these changes before deployment? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add .
            git commit -m "Pre-deployment commit: $(date)"
            log_success "Changes committed"
        else
            log_warning "Proceeding with uncommitted changes"
        fi
    fi
    
    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    log_info "Current branch: $CURRENT_BRANCH"
    
    if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
        log_warning "Not on main/master branch. Current branch: $CURRENT_BRANCH"
        read -p "Continue with deployment from this branch? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment cancelled"
            exit 1
        fi
    fi
}

test_application() {
    log_info "Running basic application tests..."
    
    # Test if the application can start
    log_info "Testing application startup..."
    
    # Create a simple test script
    cat > test_startup.py << EOF
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app_production import create_app
    app = create_app()
    print("✅ Application created successfully")
    
    with app.app_context():
        # Test basic route
        with app.test_client() as client:
            response = client.get('/health')
            if response.status_code == 200:
                print("✅ Health check endpoint working")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                sys.exit(1)
                
        print("✅ Basic tests passed")
        
except Exception as e:
    print(f"❌ Application test failed: {e}")
    sys.exit(1)
EOF
    
    # Run the test
    if python3 test_startup.py; then
        log_success "Application tests passed"
        rm test_startup.py
    else
        log_error "Application tests failed"
        rm test_startup.py
        exit 1
    fi
}

deploy_to_render() {
    log_info "Deploying to Render..."
    
    # Push to git repository (Render will auto-deploy)
    log_info "Pushing to git repository..."
    
    # Get the remote URL
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    
    if [ -z "$REMOTE_URL" ]; then
        log_error "No git remote 'origin' found. Please set up your git repository first."
        log_info "To set up git remote:"
        log_info "  git remote add origin <your-repository-url>"
        exit 1
    fi
    
    log_info "Pushing to remote: $REMOTE_URL"
    
    # Push to the repository
    if git push origin "$CURRENT_BRANCH"; then
        log_success "Code pushed to repository"
    else
        log_error "Failed to push to repository"
        exit 1
    fi
    
    log_info "Render will automatically deploy from the repository"
    log_info "Monitor deployment at: https://dashboard.render.com"
}

update_deployment_state() {
    log_info "Updating deployment state..."
    
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Create a simple deployment log entry
    cat >> deployment_log.txt << EOF
Deployment: $TIMESTAMP
Environment: $ENVIRONMENT
Platform: Render
Status: Initiated
Branch: $CURRENT_BRANCH
Commit: $(git rev-parse HEAD)
---
EOF
    
    log_success "Deployment state updated"
}

show_deployment_info() {
    log_success "Deployment initiated successfully!"
    echo
    echo "=== Deployment Information ==="
    echo "Project: $PROJECT_NAME"
    echo "Environment: $ENVIRONMENT"
    echo "Platform: Render"
    echo "Branch: $CURRENT_BRANCH"
    echo "Commit: $(git rev-parse HEAD)"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo
    echo "=== Next Steps ==="
    echo "1. Monitor deployment at: https://dashboard.render.com"
    echo "2. Check application logs for any issues"
    echo "3. Verify health check: https://magsasa-card-api-staging.onrender.com/health"
    echo "4. Test API endpoints once deployment is complete"
    echo
    echo "=== Environment Variables to Set in Render Dashboard ==="
    echo "- OPENAI_API_KEY"
    echo "- GOOGLE_AI_API_KEY"
    echo "- SECRET_KEY (if not auto-generated)"
    echo
    echo "=== Useful Commands ==="
    echo "- Check deployment status: ./deployment/scripts/check-deployment-status.sh"
    echo "- View logs: ./deployment/scripts/view-render-logs.sh"
    echo "- Rollback: ./deployment/scripts/rollback-deployment.sh"
}

# Main execution
main() {
    echo "=== $PROJECT_NAME - Render Deployment ==="
    echo
    
    check_prerequisites
    validate_configuration
    prepare_deployment
    check_git_status
    test_application
    deploy_to_render
    update_deployment_state
    show_deployment_info
    
    log_success "Deployment script completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --dry-run      Perform all checks but don't actually deploy"
        echo "  --force        Skip confirmation prompts"
        echo
        echo "This script automates deployment to Render staging environment."
        echo "It performs prerequisite checks, validates configuration, runs tests,"
        echo "and pushes code to the git repository for auto-deployment."
        exit 0
        ;;
    --dry-run)
        log_info "Running in dry-run mode - no actual deployment will occur"
        check_prerequisites
        validate_configuration
        prepare_deployment
        check_git_status
        test_application
        log_success "Dry-run completed successfully!"
        exit 0
        ;;
    --force)
        export FORCE_DEPLOY=true
        ;;
esac

# Run main function
main
