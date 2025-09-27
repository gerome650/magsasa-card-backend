"""
MAGSASA-CARD Dynamic Pricing Backend API
Main application file with proper modular structure
"""

from flask import Flask
from flask_cors import CORS
from src.database.init_db import ensure_database
from src.routes.dynamic_pricing import dynamic_pricing_bp
from src.routes.logistics import logistics_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app, origins=['*'])
    
    # Initialize database
    ensure_database()
    
    # Register blueprints
    app.register_blueprint(dynamic_pricing_bp)
    app.register_blueprint(logistics_bp)
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
