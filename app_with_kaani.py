"""
MAGSASA-CARD Enhanced Platform API with KaAni Integration
Agricultural Intelligence and Dynamic Pricing System
"""

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import os

# Import blueprints
from src.routes.dynamic_pricing import dynamic_pricing_bp
from src.routes.kaani_routes import kaani_bp

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'magsasa-card-secret-key-2025')
    app.config['DATABASE_PATH'] = 'src/database/dynamic_pricing.db'
    
    # Register blueprints
    app.register_blueprint(dynamic_pricing_bp)
    app.register_blueprint(kaani_bp)  # New KaAni integration
    
    # Root endpoint with comprehensive API information
    @app.route('/')
    def api_info():
        """API information and available endpoints"""
        return jsonify({
            "api_name": "MAGSASA-CARD Enhanced Platform API",
            "version": "2.1.0",  # Updated version with KaAni
            "description": "Agricultural Intelligence and Dynamic Pricing System with KaAni AI Integration",
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "features": [
                "Dynamic Pricing Engine",
                "Logistics Integration", 
                "Order Processing",
                "Bulk Discounts",
                "CARD Member Benefits",
                "Market Comparison",
                "Pricing Analytics",
                "KaAni Agricultural Diagnosis",  # New feature
                "AgScore Risk Assessment",      # New feature
                "AI Product Recommendations",   # New feature
                "Seasonal Guidance",           # New feature
                "A/B Testing Framework"        # New feature
            ],
            "endpoints": {
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
                },
                "kaani": {
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
            },
            "kaani_integration": {
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
            },
            "authentication": {
                "required": False,
                "card_member_benefits": True,
                "farmer_profiles": True
            },
            "data_sources": [
                "MAGSASA-CARD Product Catalog",
                "PAGASA Climate Data",
                "Agricultural Extension Knowledge Base",
                "CARD MRI Financial Data",
                "OpenAI Agricultural Intelligence",
                "Google AI Comparison Testing"
            ],
            "compliance": {
                "bsp_automated_scoring": True,
                "data_privacy_act": True,
                "transparent_ai_decisions": True,
                "audit_trail_maintained": True
            }
        })
    
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
    
    print(f"🚀 Starting MAGSASA-CARD Enhanced Platform API with KaAni Integration")
    print(f"📍 Server running on port {port}")
    print(f"🌾 KaAni Agricultural Intelligence: ENABLED")
    print(f"🎯 AgScore Risk Assessment: ENABLED")
    print(f"🤖 AI Providers: OpenAI + Google AI (A/B Testing)")
    print(f"📊 Features: Dynamic Pricing + Logistics + Agricultural Diagnosis")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
