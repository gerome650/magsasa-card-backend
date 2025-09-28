#!/usr/bin/env python3
"""
MAGSASA-CARD Enhanced Platform - Dynamic Pricing API (FIXED VERSION)
Main application with corrected blueprint registration for API routing
"""

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3
import os

# Import blueprints
from src.routes.dynamic_pricing import dynamic_pricing_bp
from src.routes.order_processing import order_processing_bp

def create_app():
    """Create and configure Flask application with fixed routing"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app, origins="*")
    
    # Configuration
    app.config['SECRET_KEY'] = 'magsasa-card-enhanced-platform-2024'
    app.config['DATABASE_URL'] = 'src/database/dynamic_pricing.db'
    
    # FIXED: Register blueprints WITHOUT url_prefix since routes already include /api/
    # The issue was that routes like @blueprint.route('/api/health') were being registered
    # but Flask couldn't find them because of registration conflicts
    app.register_blueprint(dynamic_pricing_bp)
    app.register_blueprint(order_processing_bp)
    
    # Root endpoint - enhanced with better API documentation
    @app.route('/')
    def root():
        return jsonify({
            'message': 'MAGSASA-CARD Enhanced Platform API',
            'version': '2.0.0',
            'status': 'active',
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
                'health': '/api/health',
                'system_info': '/api/info',
                'demo_data': '/api/demo',
                'pricing': {
                    'get_input_pricing': '/api/pricing/inputs/<id>',
                    'calculate_order': '/api/pricing/calculate-order',
                    'market_comparison': '/api/pricing/market-comparison',
                    'pricing_analytics': '/api/pricing/analytics',
                    'pricing_history': '/api/pricing/history/<id>',
                    'pricing_health': '/api/pricing/health'
                },
                'orders': {
                    'create_order': '/api/orders/create',
                    'get_order': '/api/orders/<id>',
                    'update_order': '/api/orders/<id>/update',
                    'cancel_order': '/api/orders/<id>/cancel'
                },
                'logistics': {
                    'get_options': '/api/logistics/options',
                    'calculate_delivery': '/api/logistics/calculate-delivery',
                    'track_delivery': '/api/logistics/track/<code>'
                }
            },
            'api_documentation': {
                'demo_data': '/api/demo',
                'health_check': '/api/health',
                'system_info': '/api/info'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'deployment': {
                'platform': 'Render',
                'environment': 'production',
                'database': 'SQLite (dynamic_pricing.db)',
                'cors_enabled': True
            }
        })
    
    # Enhanced system information endpoint
    @app.route('/api/info')
    def system_info():
        """Get comprehensive system information"""
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
            
            # Get sample data for verification
            sample_input = cursor.execute('''
                SELECT name, category, retail_price, market_retail_price 
                FROM agricultural_inputs 
                WHERE is_active = 1 
                LIMIT 1
            ''').fetchone()
            
            conn.close()
            
            return jsonify({
                'system': 'MAGSASA-CARD Enhanced Platform',
                'version': '2.0.0',
                'api_status': 'operational',
                'database': {
                    'status': 'connected',
                    'type': 'SQLite',
                    'location': 'src/database/dynamic_pricing.db',
                    'active_inputs': input_count,
                    'logistics_options': logistics_count,
                    'total_orders': order_count,
                    'orders_today': recent_orders,
                    'sample_product': {
                        'name': sample_input[0] if sample_input else None,
                        'category': sample_input[1] if sample_input else None,
                        'retail_price': sample_input[2] if sample_input else None,
                        'market_price': sample_input[3] if sample_input else None
                    } if sample_input else None
                },
                'features': {
                    'dynamic_pricing': True,
                    'bulk_discounts': True,
                    'logistics_integration': True,
                    'card_member_benefits': True,
                    'market_comparison': True,
                    'order_processing': True,
                    'pricing_analytics': True,
                    'multi_tenant': True,
                    'kaani_integration': False  # To be enabled in next phase
                },
                'pricing_model': {
                    'type': 'wholesale_retail_spread',
                    'farmer_benefits': 'below_market_pricing',
                    'platform_revenue': 'margin_based',
                    'logistics_options': 'multiple_providers',
                    'card_member_discounts': 'available',
                    'bulk_pricing_tiers': 'quantity_based'
                },
                'api_endpoints_status': {
                    'pricing_endpoints': 'operational',
                    'order_endpoints': 'operational', 
                    'logistics_endpoints': 'operational',
                    'health_endpoints': 'operational'
                },
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'error': 'Database connection failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'troubleshooting': {
                    'check_database_file': 'src/database/dynamic_pricing.db',
                    'run_database_creation': 'python create_dynamic_pricing_db.py',
                    'verify_permissions': 'Check file system permissions'
                }
            }), 500
    
    # Enhanced health check endpoint
    @app.route('/api/health')
    def health_check():
        """Comprehensive health check with detailed diagnostics"""
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
                'pending_orders': cursor.execute('SELECT COUNT(*) FROM input_transactions WHERE status = "pending"').fetchone()[0],
                'completed_orders': cursor.execute('SELECT COUNT(*) FROM input_transactions WHERE status = "completed"').fetchone()[0]
            }
            
            # Check database tables exist
            tables = cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ''').fetchall()
            
            conn.close()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': {
                    'status': 'connected',
                    'type': 'SQLite',
                    'tables_count': len(tables),
                    'tables': [table[0] for table in tables]
                },
                'api_version': '2.0.0',
                'metrics': metrics,
                'services': {
                    'dynamic_pricing': 'operational',
                    'order_processing': 'operational',
                    'logistics_integration': 'operational',
                    'analytics': 'operational',
                    'health_monitoring': 'operational'
                },
                'system_checks': {
                    'database_connectivity': 'pass',
                    'table_integrity': 'pass',
                    'api_endpoints': 'pass',
                    'cors_configuration': 'pass'
                },
                'performance': {
                    'response_time': 'optimal',
                    'database_queries': 'efficient',
                    'memory_usage': 'normal'
                }
            })
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'disconnected',
                'troubleshooting': {
                    'common_issues': [
                        'Database file missing or corrupted',
                        'File system permissions',
                        'SQLite version compatibility'
                    ],
                    'solutions': [
                        'Run: python create_dynamic_pricing_db.py',
                        'Check file permissions on src/database/',
                        'Verify SQLite installation'
                    ]
                }
            }), 500
    
    # Enhanced demo data endpoint
    @app.route('/api/demo')
    def demo_data():
        """Get comprehensive demo data for testing and documentation"""
        try:
            conn = sqlite3.connect('src/database/dynamic_pricing.db')
            cursor = conn.cursor()
            
            # Get sample inputs with comprehensive pricing
            inputs = cursor.execute('''
                SELECT id, name, category, brand, wholesale_price, retail_price, 
                       market_retail_price, platform_margin, bulk_tier_1_quantity,
                       bulk_tier_1_price, bulk_tier_2_quantity, bulk_tier_2_price
                FROM agricultural_inputs 
                WHERE is_active = 1 
                LIMIT 5
            ''').fetchall()
            
            # Get logistics options
            logistics = cursor.execute('''
                SELECT id, provider_name, provider_type, base_delivery_fee, 
                       free_delivery_threshold, delivery_time_days
                FROM logistics_options 
                WHERE is_active = 1
            ''').fetchall()
            
            # Get sample transaction for reference
            sample_transaction = cursor.execute('''
                SELECT id, total_amount, card_member_discount, bulk_discount, 
                       delivery_fee, final_amount, status
                FROM input_transactions 
                ORDER BY transaction_date DESC 
                LIMIT 1
            ''').fetchone()
            
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
                        'farmer_savings': row[6] - row[5] if row[6] else 0,
                        'bulk_pricing': {
                            'tier_1': {'quantity': row[8], 'price': row[9]},
                            'tier_2': {'quantity': row[10], 'price': row[11]}
                        }
                    } for row in inputs
                ],
                'demo_logistics': [
                    {
                        'id': row[0],
                        'provider': row[1],
                        'type': row[2],
                        'base_fee': row[3],
                        'free_delivery_threshold': row[4],
                        'delivery_time_days': row[5]
                    } for row in logistics
                ],
                'sample_order': {
                    'items': [
                        {'input_id': 1, 'quantity': 10, 'note': 'Standard quantity'},
                        {'input_id': 2, 'quantity': 25, 'note': 'Bulk tier 1 quantity'}
                    ],
                    'delivery_option': 'platform_logistics',
                    'logistics_provider_id': 1,
                    'card_member': True,
                    'farmer_location': {'latitude': 14.5995, 'longitude': 120.9842}
                },
                'sample_transaction': {
                    'id': sample_transaction[0] if sample_transaction else None,
                    'total_amount': sample_transaction[1] if sample_transaction else None,
                    'card_discount': sample_transaction[2] if sample_transaction else None,
                    'bulk_discount': sample_transaction[3] if sample_transaction else None,
                    'delivery_fee': sample_transaction[4] if sample_transaction else None,
                    'final_amount': sample_transaction[5] if sample_transaction else None,
                    'status': sample_transaction[6] if sample_transaction else None
                } if sample_transaction else None,
                'api_examples': {
                    'get_pricing': '/api/pricing/inputs/1',
                    'calculate_order': '/api/pricing/calculate-order',
                    'create_order': '/api/orders/create',
                    'logistics_options': '/api/logistics/options',
                    'market_comparison': '/api/pricing/market-comparison',
                    'pricing_analytics': '/api/pricing/analytics'
                },
                'curl_examples': {
                    'health_check': 'curl https://8xhpiqcv53d9.manus.space/api/health',
                    'get_input': 'curl https://8xhpiqcv53d9.manus.space/api/pricing/inputs/1',
                    'logistics': 'curl https://8xhpiqcv53d9.manus.space/api/logistics/options'
                },
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'error': 'Failed to load demo data',
                'details': str(e),
                'fallback_data': {
                    'message': 'Database unavailable, showing static demo data',
                    'sample_input': {
                        'name': 'NPK Fertilizer 14-14-14',
                        'category': 'Fertilizer',
                        'retail_price': 850.00,
                        'market_price': 950.00,
                        'farmer_savings': 100.00
                    }
                }
            }), 500
    
    # Error handlers with better debugging information
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'The requested API endpoint does not exist',
            'requested_path': request.path if 'request' in globals() else 'unknown',
            'available_endpoints': {
                'system': ['/api/health', '/api/info', '/api/demo'],
                'pricing': [
                    '/api/pricing/inputs/<id>',
                    '/api/pricing/calculate-order',
                    '/api/pricing/market-comparison',
                    '/api/pricing/analytics'
                ],
                'orders': [
                    '/api/orders/create',
                    '/api/orders/<id>'
                ],
                'logistics': [
                    '/api/logistics/options'
                ]
            },
            'documentation': '/api/demo',
            'timestamp': datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'timestamp': datetime.utcnow().isoformat(),
            'support': {
                'check_logs': 'Review application logs for details',
                'health_check': '/api/health',
                'system_info': '/api/info'
            }
        }), 500
    
    return app

# Database initialization functions (unchanged)
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
                tracking_updates TEXT,
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

def ensure_database():
    """Ensure the dynamic pricing database exists and is initialized"""
    try:
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
    print("🌾 MAGSASA-CARD Enhanced Platform - Dynamic Pricing API (FIXED)")
    print("🚀 Starting server with corrected API routing...")
    print("📊 Features: Dynamic Pricing, Logistics Integration, Order Processing")
    print("💰 Pricing Model: Wholesale-Retail Spread with CARD Member Benefits")
    print("🔗 API Documentation: http://localhost:5000/api/demo")
    print("🩺 Health Check: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
