#!/usr/bin/env python3
"""
MAGSASA-CARD Enhanced Platform - Main Application
Unified agricultural technology platform with enterprise-grade security
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os

# Import models and database
from src.models.user import db, bcrypt
from src.models import agricultural  # Import agricultural models

# Import routes
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.organization import organization_bp
from src.routes.permission import permission_bp
from src.routes.analytics import analytics_bp
from src.routes.tenant_management import tenant_management_bp
from src.routes.partner_api import partner_api_bp
from src.routes.partner_management import partner_management_bp
from src.routes.agricultural import agricultural_bp
from src.routes.agricultural_partners import agricultural_partners_bp
from src.routes.analytics_reporting import analytics_bp as analytics_reporting_bp

# Import middleware
from src.middleware.tenant import init_tenant_middleware
from src.middleware.partner_api import init_partner_api_middleware

def create_app(config_name='development'):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'magsasa-card-enhanced-platform-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///./src/database/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.environ.get('JWT_EXPIRATION_HOURS', 24)))
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    
    # CORS configuration
    cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS(app, origins=cors_origins)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    
    # Initialize JWT
    jwt = JWTManager(app)
    
    # Initialize middleware
    init_tenant_middleware(app)
    init_partner_api_middleware(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(organization_bp)
    app.register_blueprint(permission_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(tenant_management_bp)
    app.register_blueprint(partner_api_bp)
    app.register_blueprint(partner_management_bp)
    app.register_blueprint(agricultural_bp)
    app.register_blueprint(agricultural_partners_bp)
    app.register_blueprint(analytics_reporting_bp)
    
    # Home route
    @app.route('/')
    def home():
        """Home endpoint with system information"""
        return jsonify({
            'message': 'MAGSASA-CARD Enhanced Platform API',
            'version': '2.0.0',
            'status': 'active',
            'description': 'Unified agricultural technology platform with enterprise-grade security',
            'features': [
                'Multi-tenant agricultural operations',
                'Comprehensive farmer management',
                'Farm and crop tracking',
                'Agricultural input management',
                'Partner ecosystem integration',
                'Enterprise security and audit trails'
            ],
            'endpoints': {
                'authentication': '/api/auth/*',
                'users': '/api/users/*',
                'organizations': '/api/organizations/*',
                'agricultural': '/api/agricultural/*',
                'partners': '/api/partners/*',
                'analytics': '/api/analytics/*',
                'health': '/api/health'
            }
        })
    
    # Health check route
    @app.route('/api/health')
    def health_check():
        """Comprehensive health check"""
        try:
            from src.models.user import User, Organization
            from src.models.agricultural import Farmer, Farm, AgriculturalInput
            
            # Check database connectivity
            user_count = User.query.count()
            org_count = Organization.query.count()
            farmer_count = Farmer.query.count()
            farm_count = Farm.query.count()
            input_count = AgriculturalInput.query.count()
            
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'platform': 'MAGSASA-CARD Enhanced',
                'version': '2.0.0',
                'statistics': {
                    'users': user_count,
                    'organizations': org_count,
                    'farmers': farmer_count,
                    'farms': farm_count,
                    'agricultural_inputs': input_count
                },
                'features': {
                    'multi_tenant': True,
                    'agricultural_operations': True,
                    'partner_integration': True,
                    'security_audit': True,
                    'mobile_ready': True
                },
                'timestamp': db.func.now()
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': db.func.now()
            }), 500
    
    # System information route
    @app.route('/api/system/info')
    def system_info():
        """Get detailed system information"""
        try:
            from src.models.user import User, Organization, UserRole
            from src.models.agricultural import (
                Farmer, Farm, Crop, AgriculturalInput, FarmActivity
            )
            
            # Get comprehensive statistics
            stats = {
                'platform': {
                    'name': 'MAGSASA-CARD Enhanced Platform',
                    'version': '2.0.0',
                    'description': 'Unified agricultural technology platform',
                    'features': [
                        'Multi-tenant architecture',
                        'Comprehensive farmer management',
                        'Farm and crop tracking',
                        'Agricultural input management',
                        'Partner ecosystem integration',
                        'Enterprise security and compliance',
                        'Mobile-ready operations',
                        'Real-time analytics and reporting'
                    ]
                },
                'statistics': {
                    'users': User.query.count(),
                    'organizations': Organization.query.count(),
                    'farmers': Farmer.query.count(),
                    'farms': Farm.query.count(),
                    'crops': Crop.query.count(),
                    'agricultural_inputs': AgriculturalInput.query.count(),
                    'farm_activities': FarmActivity.query.count()
                },
                'user_roles': {
                    'administrative': ['super_admin', 'admin', 'manager'],
                    'operational': ['field_officer', 'farmer'],
                    'partners': ['input_supplier', 'logistics_partner', 'financial_partner', 'buyer_processor']
                },
                'agricultural_features': {
                    'farmer_management': True,
                    'farm_operations': True,
                    'crop_tracking': True,
                    'input_management': True,
                    'harvest_recording': True,
                    'weather_integration': True,
                    'analytics_reporting': True,
                    'mobile_operations': True
                },
                'integration_capabilities': {
                    'card_bdsfi': True,
                    'rsbsa_system': True,
                    'weather_services': True,
                    'partner_apis': True,
                    'mobile_apps': True,
                    'third_party_systems': True
                }
            }
            
            return jsonify(stats)
            
        except Exception as e:
            return jsonify({
                'error': 'Failed to fetch system information',
                'details': str(e)
            }), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'The requested API endpoint does not exist',
            'platform': 'MAGSASA-CARD Enhanced Platform',
            'available_endpoints': {
                'authentication': '/api/auth/*',
                'users': '/api/users/*',
                'organizations': '/api/organizations/*',
                'agricultural': '/api/agricultural/*',
                'partners': '/api/partners/*',
                'analytics': '/api/analytics/*',
                'system': '/api/system/*',
                'health': '/api/health'
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred in the MAGSASA-CARD Enhanced Platform',
            'platform': 'MAGSASA-CARD Enhanced Platform'
        }), 500
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token required'}), 401
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"⚠️ Database initialization warning: {str(e)}")
    
    return app

def main():
    """Main application entry point"""
    app = create_app()
    
    # Get configuration from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("🌾 Starting MAGSASA-CARD Enhanced Platform...")
    print(f"🚀 Server running on http://{host}:{port}")
    print("📱 Platform features:")
    print("   • Multi-tenant agricultural operations")
    print("   • Comprehensive farmer and farm management")
    print("   • Agricultural input and supply chain integration")
    print("   • Partner ecosystem with CARD BDSFI support")
    print("   • Enterprise-grade security and audit trails")
    print("   • Mobile-ready field operations")
    print("   • Real-time analytics and reporting")
    
    # Run the application
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
