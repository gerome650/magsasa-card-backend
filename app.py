"""
MAGSASA-CARD Enhanced Platform API with KaAni Integration - Standalone Version
Agricultural Intelligence and Dynamic Pricing System
"""

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'magsasa-card-secret-key-2025')
    app.config['DATABASE_PATH'] = 'src/database/dynamic_pricing.db'
    
    # Import and register blueprints
    try:
        from src.routes.dynamic_pricing import dynamic_pricing_bp
        app.register_blueprint(dynamic_pricing_bp)
        print("✅ Dynamic pricing blueprint registered")
    except ImportError as e:
        print(f"❌ Failed to import dynamic pricing blueprint: {e}")
    
    try:
        from src.routes.kaani_routes import kaani_bp
        app.register_blueprint(kaani_bp)
        print("✅ KaAni blueprint registered")
    except ImportError as e:
        print(f"❌ Failed to import KaAni blueprint: {e}")
    
    # Root endpoint with comprehensive API information
    @app.route('/')
    def api_info():
        """API information and available endpoints"""
        
        # Check which blueprints are actually registered
        registered_blueprints = list(app.blueprints.keys())
        kaani_enabled = 'kaani' in registered_blueprints
        
        base_response = {
            "api_name": "MAGSASA-CARD Enhanced Platform API",
            "version": "2.1.0" if kaani_enabled else "2.0.0",
            "description": "Agricultural Intelligence and Dynamic Pricing System" + (" with KaAni AI Integration" if kaani_enabled else ""),
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "deployment_info": {
                "kaani_integration": kaani_enabled,
                "registered_blueprints": registered_blueprints,
                "deployment_timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Base features
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
        
        # Base endpoints
        endpoints = {
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
            
            # Add KaAni integration details
            base_response["kaani_integration"] = {
                "agricultural_diagnosis": {
                    "modes": ["quick", "regular"],
                    "topics": ["soil_climate", "pests", "disease", "fertilization"],
                    "languages": ["english", "tagalog", "cebuano"],
                    "ai_providers": ["openai", "google_ai"]
                },
                "agscore_system": {
                    "scoring_range": "0-100",
                    "risk_tiers": ["A (Low Risk)", "B (Medium Risk)", "C (High Risk)"],
                    "modules": ["baseline_farm_profile", "financial_history", "climate_sensor_data"],
                    "bsp_compliant": True
                },
                "product_matching": {
                    "ai_powered": True,
                    "seasonal_aware": True,
                    "farmer_specific": True,
                    "confidence_scored": True
                }
            }
        
        base_response["endpoints"] = endpoints
        
        # Additional metadata
        base_response.update({
            "authentication": {
                "required": False,
                "card_member_benefits": True,
                "farmer_profiles": kaani_enabled
            },
            "data_sources": [
                "MAGSASA-CARD Product Catalog",
                "PAGASA Climate Data" if kaani_enabled else None,
                "Agricultural Extension Knowledge Base" if kaani_enabled else None,
                "CARD MRI Financial Data",
                "OpenAI Agricultural Intelligence" if kaani_enabled else None,
                "Google AI Comparison Testing" if kaani_enabled else None
            ]
        })
        
        # Remove None values
        base_response["data_sources"] = [ds for ds in base_response["data_sources"] if ds is not None]
        
        if kaani_enabled:
            base_response["compliance"] = {
                "bsp_automated_scoring": True,
                "data_privacy_act": True,
                "transparent_ai_decisions": True,
                "audit_trail_maintained": True
            }
        
        return jsonify(base_response)
    
    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Endpoint not found",
            "message": "The requested API endpoint does not exist",
            "available_endpoints": "/",
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }), 500
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Starting MAGSASA-CARD Enhanced Platform API")
    print(f"📍 Server running on port {port}")
    
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
    
    app.run(host='0.0.0.0', port=port, debug=debug)
