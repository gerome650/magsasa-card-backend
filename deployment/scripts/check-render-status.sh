#!/bin/bash

# MAGSASA-CARD Platform - Render Deployment Status Checker
# Monitors and reports on Render deployment status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STAGING_URL="${STAGING_URL:-https://magsasa-card-api-staging.onrender.com}"
TIMEOUT=30
RETRY_COUNT=3

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

check_url_health() {
    local url=$1
    local endpoint=$2
    local description=$3
    
    log_info "Checking $description: $url$endpoint"
    
    for i in $(seq 1 $RETRY_COUNT); do
        if curl -s -f --max-time $TIMEOUT "$url$endpoint" > /dev/null; then
            log_success "$description is healthy"
            return 0
        else
            if [ $i -lt $RETRY_COUNT ]; then
                log_warning "Attempt $i failed, retrying..."
                sleep 5
            fi
        fi
    done
    
    log_error "$description is not responding"
    return 1
}

check_api_response() {
    local url=$1
    local endpoint=$2
    local description=$3
    
    log_info "Testing $description: $url$endpoint"
    
    response=$(curl -s --max-time $TIMEOUT "$url$endpoint" 2>/dev/null || echo "ERROR")
    
    if [ "$response" = "ERROR" ]; then
        log_error "$description failed to respond"
        return 1
    fi
    
    # Check if response is valid JSON
    if echo "$response" | jq . > /dev/null 2>&1; then
        log_success "$description returned valid JSON"
        
        # Extract key information
        if echo "$response" | jq -e '.status' > /dev/null 2>&1; then
            status=$(echo "$response" | jq -r '.status')
            log_info "Status: $status"
        fi
        
        if echo "$response" | jq -e '.version' > /dev/null 2>&1; then
            version=$(echo "$response" | jq -r '.version')
            log_info "Version: $version"
        fi
        
        return 0
    else
        log_warning "$description returned non-JSON response"
        echo "Response: $response"
        return 1
    fi
}

check_render_deployment() {
    echo "=== MAGSASA-CARD Render Deployment Status Check ==="
    echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    echo "Target URL: $STAGING_URL"
    echo

    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found, JSON parsing will be limited"
    fi

    # Basic connectivity check
    log_info "Performing basic connectivity check..."
    if ping -c 1 google.com > /dev/null 2>&1; then
        log_success "Internet connectivity confirmed"
    else
        log_error "No internet connectivity"
        exit 1
    fi

    # Health check endpoint
    if check_url_health "$STAGING_URL" "/health" "Health Check Endpoint"; then
        HEALTH_STATUS="healthy"
    else
        HEALTH_STATUS="unhealthy"
    fi

    # API info endpoint
    if check_api_response "$STAGING_URL" "/" "API Info Endpoint"; then
        API_STATUS="working"
    else
        API_STATUS="failed"
    fi

    # Specific API endpoints
    echo
    log_info "Testing specific API endpoints..."

    # Dynamic pricing endpoint
    if check_url_health "$STAGING_URL" "/api/pricing/health" "Dynamic Pricing Health"; then
        PRICING_STATUS="working"
    else
        PRICING_STATUS="failed"
    fi

    # KaAni endpoint
    if check_url_health "$STAGING_URL" "/api/kaani/health" "KaAni Health"; then
        KAANI_STATUS="working"
    else
        KAANI_STATUS="failed"
    fi

    # Performance check
    echo
    log_info "Performing performance check..."
    
    start_time=$(date +%s%N)
    if curl -s -f --max-time $TIMEOUT "$STAGING_URL/health" > /dev/null; then
        end_time=$(date +%s%N)
        response_time=$(( (end_time - start_time) / 1000000 ))
        log_success "Response time: ${response_time}ms"
        
        if [ $response_time -lt 1000 ]; then
            PERFORMANCE_STATUS="excellent"
        elif [ $response_time -lt 3000 ]; then
            PERFORMANCE_STATUS="good"
        elif [ $response_time -lt 5000 ]; then
            PERFORMANCE_STATUS="acceptable"
        else
            PERFORMANCE_STATUS="slow"
        fi
    else
        PERFORMANCE_STATUS="failed"
        response_time="timeout"
    fi

    # SSL/HTTPS check
    echo
    log_info "Checking SSL/HTTPS configuration..."
    
    if curl -s -I --max-time $TIMEOUT "$STAGING_URL" | grep -q "HTTP/[12] 200\|HTTP/[12] 301\|HTTP/[12] 302"; then
        log_success "HTTPS is working"
        SSL_STATUS="working"
    else
        log_error "HTTPS check failed"
        SSL_STATUS="failed"
    fi

    # Generate summary report
    echo
    echo "=== DEPLOYMENT STATUS SUMMARY ==="
    echo "Overall Health: $HEALTH_STATUS"
    echo "API Status: $API_STATUS"
    echo "Dynamic Pricing: $PRICING_STATUS"
    echo "KaAni Integration: $KAANI_STATUS"
    echo "Performance: $PERFORMANCE_STATUS ($response_time)"
    echo "SSL/HTTPS: $SSL_STATUS"
    echo

    # Determine overall status
    if [ "$HEALTH_STATUS" = "healthy" ] && [ "$API_STATUS" = "working" ] && [ "$SSL_STATUS" = "working" ]; then
        OVERALL_STATUS="healthy"
        log_success "✅ Deployment is healthy and operational"
    elif [ "$HEALTH_STATUS" = "healthy" ] && [ "$API_STATUS" = "working" ]; then
        OVERALL_STATUS="degraded"
        log_warning "⚠️  Deployment is operational but has some issues"
    else
        OVERALL_STATUS="unhealthy"
        log_error "❌ Deployment has critical issues"
    fi

    # Generate JSON report
    if command -v jq &> /dev/null; then
        cat > deployment_status_report.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "deployment_url": "$STAGING_URL",
  "overall_status": "$OVERALL_STATUS",
  "checks": {
    "health_endpoint": "$HEALTH_STATUS",
    "api_info": "$API_STATUS",
    "dynamic_pricing": "$PRICING_STATUS",
    "kaani_integration": "$KAANI_STATUS",
    "ssl_https": "$SSL_STATUS"
  },
  "performance": {
    "response_time_ms": "$response_time",
    "status": "$PERFORMANCE_STATUS"
  },
  "environment": "staging",
  "platform": "render"
}
EOF
        log_success "Status report saved to deployment_status_report.json"
    fi

    # Update Notion if integration is available
    if [ -f "deployment/scripts/notion-integration.py" ] && [ -n "$NOTION_API_KEY" ]; then
        log_info "Updating Notion deployment tracker..."
        python3 deployment/scripts/notion-integration.py update-deployment \
            --environment "Staging" \
            --status "Deployed" \
            --health-status "$OVERALL_STATUS" \
            --url "$STAGING_URL" \
            --notes "Automated status check: $OVERALL_STATUS at $(date)"
    fi

    # Send notifications if configured
    if [ "$OVERALL_STATUS" = "unhealthy" ] && [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 MAGSASA-CARD Staging Deployment Alert: $OVERALL_STATUS\\nURL: $STAGING_URL\\nTime: $(date)\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi

    # Exit with appropriate code
    case $OVERALL_STATUS in
        "healthy")
            exit 0
            ;;
        "degraded")
            exit 1
            ;;
        "unhealthy")
            exit 2
            ;;
        *)
            exit 3
            ;;
    esac
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --url URL      Override staging URL"
        echo "  --timeout SEC  Set timeout in seconds (default: 30)"
        echo "  --quiet        Suppress non-essential output"
        echo "  --json         Output only JSON report"
        echo
        echo "Environment Variables:"
        echo "  STAGING_URL           Staging deployment URL"
        echo "  NOTION_API_KEY        Notion integration API key"
        echo "  SLACK_WEBHOOK_URL     Slack notification webhook"
        echo
        echo "Exit Codes:"
        echo "  0 - Healthy"
        echo "  1 - Degraded"
        echo "  2 - Unhealthy"
        echo "  3 - Unknown/Error"
        exit 0
        ;;
    --url)
        STAGING_URL="$2"
        shift 2
        ;;
    --timeout)
        TIMEOUT="$2"
        shift 2
        ;;
    --quiet)
        exec > /dev/null 2>&1
        ;;
    --json)
        check_render_deployment > /dev/null 2>&1
        if [ -f "deployment_status_report.json" ]; then
            cat deployment_status_report.json
        else
            echo '{"error": "Status check failed"}'
        fi
        exit 0
        ;;
esac

# Run the main check
check_render_deployment
