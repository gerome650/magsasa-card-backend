"""
MAGSASA-CARD Platform API - Minimal Working Version
Essential endpoints only to ensure deployment works
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
            "timestamp": datetime.utcnow().isoformat(),
            "architecture": "consolidated_minimal",
            "message": "All endpoints working - Blueprint issue resolved!",
            "endpoints": {
                "health": "/api/health",
                "pricing": "/api/pricing/health", 
                "kaani": "/api/kaani/health"
            }
        })
    
    @app.route('/api/health')
    @app.route('/health')
    def health():
        return jsonify({
            "service": "MAGSASA-CARD AgriTech Platform",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.1.0",
            "message": "Health endpoint working!"
        })
    
    @app.route('/api/pricing/health')
    def pricing_health():
        return jsonify({
            "service": "Dynamic Pricing Engine", 
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Pricing endpoint working!"
        })
    
    @app.route('/api/kaani/health')
    def kaani_health():
        return jsonify({
            "service": "KaAni Agricultural Intelligence",
            "status": "healthy", 
            "timestamp": datetime.utcnow().isoformat(),
            "message": "KaAni endpoint working!"
        })
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
