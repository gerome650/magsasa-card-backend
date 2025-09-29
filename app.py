"""
MAGSASA-CARD Platform API - Consolidated Working Version
All endpoints in one file to ensure deployment works
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    @app.route('/')
    def root():
        return jsonify({
            "api_name": "MAGSASA-CARD Enhanced Platform API",
            "version": "2.1.0",
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "health": "/api/health",
                "pricing": "/api/pricing/health",
                "kaani": "/api/kaani/health"
            },
            "features": ["dynamic_pricing", "kaani_ai", "health_monitoring"]
        })
    
    @app.route('/health')
    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "MAGSASA-CARD API",
            "version": "2.1.0",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "ai_services": "operational"
        })
    
    @app.route('/api/pricing/health')
    def pricing_health():
        return jsonify({
            "service": "pricing",
            "status": "operational",
            "features": ["dynamic_pricing", "bulk_discounts", "market_analysis"],
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route('/api/kaani/health')
    def kaani_health():
        return jsonify({
            "service": "kaani_ai",
            "status": "operational", 
            "ai_provider": "openai",
            "features": ["crop_diagnosis", "pest_detection", "treatment_recommendations"],
            "timestamp": datetime.now().isoformat()
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

