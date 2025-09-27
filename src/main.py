# Duplicate the main app functionality in src/main.py for deployment compatibility
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3
import sys
import os

# Add the parent directory to the path to import routes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import blueprints from the routes directory
from src.routes.dynamic_pricing import dynamic_pricing_bp
from src.routes.order_processing import order_processing_bp

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app, origins="*")
    
    # Configuration
    app.config['SECRET_KEY'] = 'magsasa-card-enhanced-platform-2024'
    app.config['DATABASE_URL'] = 'src/database/dynamic_pricing.db'
    
    # Register blueprints
    app.register_blueprint(dynamic_pricing_bp)
    app.register_blueprint(order_processing_bp)
    
    # Root endpoint
    @app.route('/')
    def root():
        return jsonify({
            'message': 'MAGSASA-CARD Enhanced Platform API',
            'version': '2.0.0',
            'features': [
                'dynamic_pricing',
                'logistics_integration',
                'order_processing',
                'bulk_discounts',
                'card_member_benefits',
                'market_comparison',
                'pricing_analytics'
            ],
            'endpoints': {
                'pricing': '/api/pricing/*',
                'orders': '/api/orders/*',
                'logistics': '/api/logistics/*',
                'health': '/api/health'
            },
            'status': 'active',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
