#!/bin/bash

# MAGSASA-CARD Platform - Environment Setup Script
# Automates environment setup for development, staging, and production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="MAGSASA-CARD Platform"
PYTHON_VERSION="3.11"
VENV_NAME="venv"

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

show_help() {
    echo "Usage: $0 [ENVIRONMENT] [OPTIONS]"
    echo
    echo "ENVIRONMENT:"
    echo "  development    Set up development environment"
    echo "  staging        Set up staging environment"
    echo "  production     Set up production environment"
    echo
    echo "OPTIONS:"
    echo "  --help, -h     Show this help message"
    echo "  --clean        Clean existing environment before setup"
    echo "  --no-venv      Skip virtual environment creation"
    echo "  --no-deps      Skip dependency installation"
    echo "  --no-db        Skip database initialization"
    echo
    echo "Examples:"
    echo "  $0 development"
    echo "  $0 staging --clean"
    echo "  $0 production --no-venv"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        log_info "Python version: $PYTHON_VER"
        
        if [ "$PYTHON_VER" != "3.11" ] && [ "$PYTHON_VER" != "3.10" ] && [ "$PYTHON_VER" != "3.9" ]; then
            log_warning "Python 3.9+ recommended, found $PYTHON_VER"
        fi
    else
        log_error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not found"
        exit 1
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        log_warning "Git not found - version control features will be limited"
    fi
    
    log_success "Prerequisites check completed"
}

setup_virtual_environment() {
    if [ "$NO_VENV" = true ]; then
        log_info "Skipping virtual environment setup"
        return
    fi
    
    log_info "Setting up virtual environment..."
    
    # Clean existing virtual environment if requested
    if [ "$CLEAN_ENV" = true ] && [ -d "$VENV_NAME" ]; then
        log_info "Cleaning existing virtual environment..."
        rm -rf "$VENV_NAME"
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_NAME" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv "$VENV_NAME"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_NAME/bin/activate"
    log_success "Virtual environment activated"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    log_success "Pip upgraded"
}

install_dependencies() {
    if [ "$NO_DEPS" = true ]; then
        log_info "Skipping dependency installation"
        return
    fi
    
    log_info "Installing dependencies for $ENVIRONMENT environment..."
    
    # Determine requirements file
    case $ENVIRONMENT in
        development)
            REQUIREMENTS_FILE="requirements.txt"
            ;;
        staging|production)
            REQUIREMENTS_FILE="requirements_production.txt"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    # Check if requirements file exists
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        log_error "Requirements file not found: $REQUIREMENTS_FILE"
        exit 1
    fi
    
    # Install dependencies
    log_info "Installing from $REQUIREMENTS_FILE..."
    pip install -r "$REQUIREMENTS_FILE"
    log_success "Dependencies installed"
    
    # Install development dependencies if in development mode
    if [ "$ENVIRONMENT" = "development" ]; then
        log_info "Installing development dependencies..."
        pip install pytest pytest-flask black flake8 mypy
        log_success "Development dependencies installed"
    fi
}

setup_environment_variables() {
    log_info "Setting up environment variables..."
    
    ENV_FILE="deployment/configs/.env.$ENVIRONMENT"
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
    
    # Copy environment file to .env for local use
    if [ "$ENVIRONMENT" = "development" ]; then
        cp "$ENV_FILE" .env
        log_success "Environment variables copied to .env"
    else
        log_info "Environment file available at: $ENV_FILE"
        log_warning "For staging/production, set environment variables in your deployment platform"
    fi
    
    # Show required environment variables
    log_info "Required environment variables for $ENVIRONMENT:"
    case $ENVIRONMENT in
        development)
            echo "  - OPENAI_API_KEY (optional for development)"
            echo "  - GOOGLE_AI_API_KEY (optional for development)"
            ;;
        staging)
            echo "  - OPENAI_API_KEY (required)"
            echo "  - GOOGLE_AI_API_KEY (required)"
            echo "  - SECRET_KEY (auto-generated in Render)"
            ;;
        production)
            echo "  - OPENAI_API_KEY (required - use AWS Secrets Manager)"
            echo "  - GOOGLE_AI_API_KEY (required - use AWS Secrets Manager)"
            echo "  - SECRET_KEY (required - use AWS Secrets Manager)"
            echo "  - DATABASE_URL (required for PostgreSQL)"
            ;;
    esac
}

initialize_database() {
    if [ "$NO_DB" = true ]; then
        log_info "Skipping database initialization"
        return
    fi
    
    log_info "Initializing database..."
    
    # Create database directory
    mkdir -p src/database
    
    # Initialize database based on environment
    case $ENVIRONMENT in
        development)
            log_info "Setting up SQLite database for development..."
            if [ -f "create_dynamic_pricing_db.py" ]; then
                python create_dynamic_pricing_db.py
                log_success "Development database initialized"
            else
                log_warning "Database initialization script not found"
            fi
            ;;
        staging)
            log_info "Database will be initialized automatically in Render"
            ;;
        production)
            log_info "Database setup required in AWS RDS"
            log_warning "Run database migration scripts after AWS setup"
            ;;
    esac
}

create_directories() {
    log_info "Creating necessary directories..."
    
    # Create standard directories
    mkdir -p logs
    mkdir -p uploads
    mkdir -p backups
    mkdir -p tmp
    
    # Create environment-specific directories
    case $ENVIRONMENT in
        development)
            mkdir -p tests
            mkdir -p docs
            ;;
        staging|production)
            mkdir -p monitoring
            mkdir -p scripts
            ;;
    esac
    
    log_success "Directories created"
}

setup_git_hooks() {
    if ! command -v git &> /dev/null || [ ! -d ".git" ]; then
        log_info "Skipping git hooks setup (not a git repository)"
        return
    fi
    
    log_info "Setting up git hooks..."
    
    # Create pre-commit hook for development
    if [ "$ENVIRONMENT" = "development" ]; then
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for MAGSASA-CARD Platform

echo "Running pre-commit checks..."

# Check Python syntax
if command -v python3 &> /dev/null; then
    python3 -m py_compile app_production.py
    if [ $? -ne 0 ]; then
        echo "Python syntax error in app_production.py"
        exit 1
    fi
fi

# Run basic tests if available
if [ -f "test_startup.py" ]; then
    python3 test_startup.py
    if [ $? -ne 0 ]; then
        echo "Basic tests failed"
        exit 1
    fi
fi

echo "Pre-commit checks passed"
EOF
        chmod +x .git/hooks/pre-commit
        log_success "Git pre-commit hook installed"
    fi
}

run_tests() {
    if [ "$ENVIRONMENT" != "development" ]; then
        log_info "Skipping tests for $ENVIRONMENT environment"
        return
    fi
    
    log_info "Running basic tests..."
    
    # Test application startup
    cat > test_environment_setup.py << 'EOF'
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    try:
        from app_production import create_app
        print("✅ Application imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_app_creation():
    try:
        from app_production import create_app
        app = create_app()
        print("✅ Application creation successful")
        return True
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return False

def test_basic_routes():
    try:
        from app_production import create_app
        app = create_app()
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Basic routes working")
                return True
            else:
                print(f"❌ Route test failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Route test failed: {e}")
        return False

if __name__ == "__main__":
    tests = [test_imports, test_app_creation, test_basic_routes]
    passed = 0
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
EOF
    
    if python test_environment_setup.py; then
        log_success "Environment tests passed"
        rm test_environment_setup.py
    else
        log_warning "Some environment tests failed"
        rm test_environment_setup.py
    fi
}

show_completion_info() {
    log_success "Environment setup completed successfully!"
    echo
    echo "=== Environment Information ==="
    echo "Environment: $ENVIRONMENT"
    echo "Python: $(python --version 2>&1)"
    echo "Pip: $(pip --version | cut -d' ' -f1,2)"
    if [ "$NO_VENV" != true ]; then
        echo "Virtual Environment: $VENV_NAME"
    fi
    echo
    echo "=== Next Steps ==="
    case $ENVIRONMENT in
        development)
            echo "1. Activate virtual environment: source $VENV_NAME/bin/activate"
            echo "2. Set your API keys in .env file"
            echo "3. Run the application: python app_production.py"
            echo "4. Access the API at: http://localhost:5000"
            echo "5. Run tests: pytest"
            ;;
        staging)
            echo "1. Commit your changes to git"
            echo "2. Set environment variables in Render dashboard"
            echo "3. Deploy to Render: ./deployment/scripts/deploy-to-render.sh"
            echo "4. Monitor deployment at: https://dashboard.render.com"
            ;;
        production)
            echo "1. Set up AWS infrastructure"
            echo "2. Configure AWS Secrets Manager"
            echo "3. Set up RDS PostgreSQL database"
            echo "4. Deploy using AWS deployment scripts"
            echo "5. Configure monitoring and alerts"
            ;;
    esac
    echo
    echo "=== Useful Commands ==="
    echo "- Check application health: curl http://localhost:5000/health"
    echo "- View logs: tail -f logs/magsasa_card.log"
    echo "- Run deployment: ./deployment/scripts/deploy-to-render.sh"
}

# Parse command line arguments
ENVIRONMENT=""
CLEAN_ENV=false
NO_VENV=false
NO_DEPS=false
NO_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        development|staging|production)
            ENVIRONMENT="$1"
            shift
            ;;
        --clean)
            CLEAN_ENV=true
            shift
            ;;
        --no-venv)
            NO_VENV=true
            shift
            ;;
        --no-deps)
            NO_DEPS=true
            shift
            ;;
        --no-db)
            NO_DB=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate environment argument
if [ -z "$ENVIRONMENT" ]; then
    log_error "Environment argument is required"
    show_help
    exit 1
fi

# Main execution
main() {
    echo "=== $PROJECT_NAME - Environment Setup ==="
    echo "Setting up $ENVIRONMENT environment..."
    echo
    
    check_prerequisites
    setup_virtual_environment
    install_dependencies
    setup_environment_variables
    initialize_database
    create_directories
    setup_git_hooks
    run_tests
    show_completion_info
    
    log_success "Environment setup script completed successfully!"
}

# Run main function
main
