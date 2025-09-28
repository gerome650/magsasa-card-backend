"""
MAGSASA-CARD Enhanced Platform API - Production Version
Agricultural Intelligence and Dynamic Pricing System with KaAni Integration
Production-ready with enhanced logging, monitoring, and error handling
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import traceback

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging(app):
    """Configure production logging"""
    if not app.debug:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # File handler for application logs
        file_handler = RotatingFileHandler('logs/magsasa_card.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('MAGSASA-CARD Platform startup')

def create_app():
    """Create and configure Flask application for production"""
    app = Flask(__name__)
    
    # Production configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'magsasa-card-production-secret-2025')
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'src/database/dynamic_pricing.db')
    app.config['ENVIRONMENT'] = os.environ.get('ENVIRONMENT', 'production')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database configuration
    if os.environ.get('DATABASE_URL'):
        # PostgreSQL for production
        app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')
        app.config['DATABASE_TYPE'] = 'postgresql'
    else:
        # SQLite for development/testing
        app.config['DATABASE_TYPE'] = 'sqlite'
    
    # AI Configuration
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
    app.config['GOOGLE_AI_API_KEY'] = os.environ.get('GOOGLE_AI_API_KEY')
    
    # Enable CORS with production settings
    CORS(app, origins=os.environ.get('ALLOWED_ORIGINS', '*').split(','))
    
    # Setup logging
    setup_logging(app)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Production health check endpoint"""
        try:
            # Basic health checks
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "environment": app.config['ENVIRONMENT'],
                "version": "2.1.0",
                "database": {
                    "type": app.config['DATABASE_TYPE'],
                    "status": "connected"
                },
                "ai_services": {
                    "openai": bool(app.config.get('OPENAI_API_KEY')),
                    "google_ai": bool(app.config.get('GOOGLE_AI_API_KEY'))
                }
            }
            
            # Check database connectivity
            try:
                if app.config['DATABASE_TYPE'] == 'postgresql':
                    # PostgreSQL health check would go here
                    pass
                else:
                    # SQLite health check
                    import sqlite3
                    conn = sqlite3.connect(app.config['DATABASE_PATH'])
                    conn.execute('SELECT 1')
                    conn.close()
            except Exception as e:
                health_status["database"]["status"] = "error"
                health_status["database"]["error"] = str(e)
                health_status["status"] = "degraded"
            
            return jsonify(health_status), 200 if health_status["status"] == "healthy" else 503
            
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }), 503
    
    # Import and register blueprints with error handling
    blueprints_status = {}
    
    try:
        from src.routes.dynamic_pricing import dynamic_pricing_bp
        app.register_blueprint(dynamic_pricing_bp)
        blueprints_status['dynamic_pricing'] = 'registered'
        app.logger.info("✅ Dynamic pricing blueprint registered")
    except ImportError as e:
        blueprints_status['dynamic_pricing'] = f'failed: {str(e)}'
        app.logger.error(f"❌ Failed to import dynamic pricing blueprint: {e}")
    
    try:
        from src.routes.kaani_routes import kaani_bp
        app.register_blueprint(kaani_bp)
        blueprints_status['kaani'] = 'registered'
        app.logger.info("✅ KaAni blueprint registered")
    except ImportError as e:
        blueprints_status['kaani'] = f'failed: {str(e)}'
        app.logger.error(f"❌ Failed to import KaAni blueprint: {e}")
    
    try:
        from src.routes.logistics import logistics_bp
        app.register_blueprint(logistics_bp)
        blueprints_status['logistics'] = 'registered'
        app.logger.info("✅ Logistics blueprint registered")
    except ImportError as e:
        blueprints_status['logistics'] = f'failed: {str(e)}'
        app.logger.error(f"❌ Failed to import logistics blueprint: {e}")
    
    # Root endpoint with comprehensive API information
    @app.route('/')
    def api_info():
        """Production API information and available endpoints"""
        
        # Check which blueprints are actually registered
        registered_blueprints = list(app.blueprints.keys())
        kaani_enabled = 'kaani' in registered_blueprints
        
        base_response = {
            "api_name": "MAGSASA-CARD Enhanced Platform API",
            "version": "2.1.0",
            "description": "Agricultural Intelligence and Dynamic Pricing System with KaAni AI Integration",
            "status": "active",
            "environment": app.config['ENVIRONMENT'],
            "timestamp": datetime.utcnow().isoformat(),
            "deployment_info": {
                "kaani_integration": kaani_enabled,
                "registered_blueprints": registered_blueprints,
                "blueprints_status": blueprints_status,
                "deployment_timestamp": datetime.utcnow().isoformat(),
                "database_type": app.config['DATABASE_TYPE']
            }
        }
        
        # Features
        features = [
            "Dynamic Pricing Engine",
            "Logistics Integration", 
            "Order Processing",
            "Bulk Discounts",
            "CARD Member Benefits",
            "Market Comparison",
            "Pricing Analytics"
        ]
        
        # Add KaAni features if enabled
        if kaani_enabled:
            features.extend([
                "KaAni Agricultural Diagnosis",
                "AgScore Risk Assessment",
                "AI Product Recommendations",
                "Seasonal Guidance",
                "A/B Testing Framework"
            ])
        
        base_response["features"] = features
        
        # Endpoints
        endpoints = {
            "system": {
                "health": "/health",
                "info": "/",
                "metrics": "/metrics" if app.config['ENVIRONMENT'] == 'production' else None
            },
            "pricing": {
                "health": "/api/pricing/health",
                "inputs": "/api/pricing/inputs/<input_id>",
                "bulk_pricing": "/api/pricing/bulk/<input_id>",
                "card_pricing": "/api/pricing/card/<input_id>",
                "market_comparison": "/api/pricing/market-comparison/<input_id>",
                "analytics": "/api/pricing/analytics"
            },
            "logistics": {
                "options": "/api/logistics/options",
                "calculate": "/api/logistics/calculate",
                "providers": "/api/logistics/providers",
                "coverage": "/api/logistics/coverage/<location>"
            },
            "orders": {
                "create": "/api/orders/create",
                "status": "/api/orders/<order_id>/status",
                "history": "/api/orders/farmer/<farmer_id>"
            }
        }
        
        # Add KaAni endpoints if enabled
        if kaani_enabled:
            endpoints["kaani"] = {
                "health": "/api/kaani/health",
                "quick_diagnosis": "/api/kaani/quick-diagnosis",
                "regular_diagnosis": "/api/kaani/regular-diagnosis",
                "diagnosis_session": "/api/kaani/diagnosis/<session_id>",
                "agscore_assess": "/api/agscore/assess-farmer",
                "agscore_get": "/api/agscore/farmer/<farmer_id>",
                "risk_tier": "/api/agscore/risk-tier/<farmer_id>",
                "recommendations": "/api/products/kaani-recommended/<farmer_id>",
                "match_products": "/api/products/match-diagnosis",
                "farmer_profile": "/api/farmers/profile/<farmer_id>",
                "create_profile": "/api/farmers/profile",
                "ab_testing": "/api/testing/assign-farmer",
                "test_results": "/api/testing/results/<test_name>"
            }
        
        # Remove None values
        for category in endpoints:
            endpoints[category] = {k: v for k, v in endpoints[category].items() if v is not None}
        
        base_response["endpoints"] = endpoints
        
        return jsonify(base_response)
    
    # Request logging middleware
    @app.before_request
    def log_request_info():
        if app.config['ENVIRONMENT'] == 'production':
            app.logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")
    
    # Global error handlers with enhanced logging
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f"404 error: {request.url}")
        return jsonify({
            "error": "Endpoint not found",
            "message": "The requested API endpoint does not exist",
            "available_endpoints": "/",
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {str(error)}\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "error": "Unexpected error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }), 500
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Production server configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting MAGSASA-CARD Enhanced Platform API (Production)")
    print(f"📍 Server running on port {port}")
    print(f"🌍 Environment: {app.config['ENVIRONMENT']}")
    print(f"🗄️  Database: {app.config['DATABASE_TYPE']}")
    
    # Check KaAni integration status
    with app.app_context():
        if 'kaani' in app.blueprints:
            print(f"🌾 KaAni Agricultural Intelligence: ENABLED")
            print(f"🎯 AgScore Risk Assessment: ENABLED")
            print(f"🤖 AI Providers: OpenAI + Google AI (A/B Testing)")
            print(f"📊 Features: Dynamic Pricing + Logistics + Agricultural Diagnosis")
        else:
            print(f"⚠️  KaAni Agricultural Intelligence: DISABLED (Import failed)")
            print(f"📊 Features: Dynamic Pricing + Logistics only")
    
    # Use gunicorn in production, Flask dev server otherwise
    if app.config['ENVIRONMENT'] == 'production':
        print("🔧 Use gunicorn for production deployment")
        print("   gunicorn --bind 0.0.0.0:$PORT app_production:app")
    else:
        app.run(host='0.0.0.0', port=port, debug=debug)
