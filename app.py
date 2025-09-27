#!/usr/bin/env python3
"""
MAGSASA-CARD Enhanced Platform - Dynamic Pricing API
Main application with dynamic pricing and logistics endpoints
"""

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3

# Import blueprints
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
    
    # System information endpoint
    @app.route('/api/info')
    def system_info():
        """Get system information"""
        try:
            conn = sqlite3.connect('src/database/dynamic_pricing.db')
            cursor = conn.cursor()
            
            # Get database statistics
            input_count = cursor.execute('SELECT COUNT(*) FROM agricultural_inputs WHERE is_active = 1').fetchone()[0]
            logistics_count = cursor.execute('SELECT COUNT(*) FROM logistics_options WHERE is_active = 1').fetchone()[0]
            order_count = cursor.execute('SELECT COUNT(*) FROM input_transactions').fetchone()[0]
            
            # Get recent activity
            recent_orders = cursor.execute('''
                SELECT COUNT(*) FROM input_transactions 
                WHERE DATE(transaction_date) = DATE('now')
            ''').fetchone()[0]
            
            conn.close()
            
            return jsonify({
                'system': 'MAGSASA-CARD Enhanced Platform',
                'version': '2.0.0',
                'database': {
                    'status': 'connected',
                    'active_inputs': input_count,
                    'logistics_options': logistics_count,
                    'total_orders': order_count,
                    'orders_today': recent_orders
                },
                'features': {
                    'dynamic_pricing': True,
                    'bulk_discounts': True,
                    'logistics_integration': True,
                    'card_member_benefits': True,
                    'market_comparison': True,
                    'order_processing': True,
                    'pricing_analytics': True,
                    'multi_tenant': True
                },
                'pricing_model': {
                    'type': 'wholesale_retail_spread',
                    'farmer_benefits': 'below_market_pricing',
                    'platform_revenue': 'margin_based',
                    'logistics_options': 'multiple_providers',
                    'card_member_discounts': 'available'
                },
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'error': 'Database connection failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        """Comprehensive health check"""
        try:
            conn = sqlite3.connect('src/database/dynamic_pricing.db')
            cursor = conn.cursor()
            
            # Test database connectivity
            cursor.execute('SELECT 1')
            
            # Get system metrics
            metrics = {
                'active_inputs': cursor.execute('SELECT COUNT(*) FROM agricultural_inputs WHERE is_active = 1').fetchone()[0],
                'logistics_options': cursor.execute('SELECT COUNT(*) FROM logistics_options WHERE is_active = 1').fetchone()[0],
                'total_orders': cursor.execute('SELECT COUNT(*) FROM input_transactions').fetchone()[0],
                'pending_orders': cursor.execute('SELECT COUNT(*) FROM input_transactions WHERE status = "pending"').fetchone()[0]
            }
            
            conn.close()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'connected',
                'api_version': '2.0.0',
                'metrics': metrics,
                'services': {
                    'dynamic_pricing': 'operational',
                    'order_processing': 'operational',
                    'logistics_integration': 'operational',
                    'analytics': 'operational'
                }
            })
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'disconnected'
            }), 500
    
    # Demo data endpoint
    @app.route('/api/demo')
    def demo_data():
        """Get demo data for testing"""
        try:
            conn = sqlite3.connect('src/database/dynamic_pricing.db')
            cursor = conn.cursor()
            
            # Get sample inputs with pricing
            inputs = cursor.execute('''
                SELECT id, name, category, brand, wholesale_price, retail_price, market_retail_price, platform_margin
                FROM agricultural_inputs 
                WHERE is_active = 1 
                LIMIT 5
            ''').fetchall()
            
            # Get logistics options
            logistics = cursor.execute('''
                SELECT id, provider_name, provider_type, base_delivery_fee, free_delivery_threshold
                FROM logistics_options 
                WHERE is_active = 1
            ''').fetchall()
            
            conn.close()
            
            return jsonify({
                'demo_inputs': [
                    {
                        'id': row[0],
                        'name': row[1],
                        'category': row[2],
                        'brand': row[3],
                        'wholesale_price': row[4],
                        'retail_price': row[5],
                        'market_price': row[6],
                        'platform_margin': row[7],
                        'farmer_savings': row[6] - row[5] if row[6] else 0
                    } for row in inputs
                ],
                'demo_logistics': [
                    {
                        'id': row[0],
                        'provider': row[1],
                        'type': row[2],
                        'base_fee': row[3],
                        'free_delivery_threshold': row[4]
                    } for row in logistics
                ],
                'sample_order': {
                    'items': [
                        {'input_id': 1, 'quantity': 10},
                        {'input_id': 2, 'quantity': 5}
                    ],
                    'delivery_option': 'platform_logistics',
                    'logistics_provider_id': 1,
                    'card_member': True
                },
                'api_examples': {
                    'get_pricing': '/api/pricing/inputs/1',
                    'calculate_order': '/api/pricing/calculate-order',
                    'create_order': '/api/orders/create',
                    'logistics_options': '/api/logistics/options',
                    'market_comparison': '/api/pricing/market-comparison'
                }
            })
            
        except Exception as e:
            return jsonify({
                'error': 'Failed to load demo data',
                'details': str(e)
            }), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'The requested API endpoint does not exist',
            'available_endpoints': [
                '/api/pricing/inputs/<id>',
                '/api/pricing/calculate-order',
                '/api/orders/create',
                '/api/orders/<id>',
                '/api/logistics/options',
                '/api/health'
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'timestamp': datetime.utcnow().isoformat()
        }), 500
    
    return app

# Create delivery_orders table if it doesn't exist
def ensure_delivery_table():
    """Ensure delivery_orders table exists"""
    try:
        conn = sqlite3.connect('src/database/dynamic_pricing.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivery_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                logistics_option_id INTEGER,
                delivery_code VARCHAR(50) UNIQUE NOT NULL,
                pickup_address TEXT,
                delivery_address TEXT NOT NULL,
                scheduled_delivery_date TIMESTAMP,
                actual_delivery_date TIMESTAMP,
                current_status VARCHAR(20) DEFAULT 'pending',
                tracking_updates TEXT, -- JSON string
                delivery_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES input_transactions (id),
                FOREIGN KEY (logistics_option_id) REFERENCES logistics_options (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Delivery orders table ensured")
        
    except Exception as e:
        print(f"❌ Error creating delivery table: {e}")

# Database initialization function
def ensure_database():
    """Ensure the dynamic pricing database exists and is initialized"""
    try:
        import os
        db_path = 'src/database/dynamic_pricing.db'
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # If database doesn't exist, create it
        if not os.path.exists(db_path):
            print("🔧 Creating dynamic pricing database...")
            import subprocess
            subprocess.run(['python', 'create_dynamic_pricing_db.py'], check=True)
            print("✅ Database created successfully")
        else:
            print("✅ Database already exists")
            
    except Exception as e:
        print(f"❌ Error ensuring database: {e}")

# Initialize for production deployment
ensure_database()
ensure_delivery_table()

# Create the app instance for gunicorn
app = create_app()

if __name__ == '__main__':
    print("🌾 MAGSASA-CARD Enhanced Platform - Dynamic Pricing API")
    print("🚀 Starting server with dynamic pricing features...")
    print("📊 Features: Dynamic Pricing, Logistics Integration, Order Processing")
    print("💰 Pricing Model: Wholesale-Retail Spread with CARD Member Benefits")
    print("🔗 API Documentation: http://localhost:5000/api/demo")
    
    app.run(host='0.0.0.0', port=5000, debug=True)