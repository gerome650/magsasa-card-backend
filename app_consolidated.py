"""
MAGSASA-CARD Enhanced Platform API - Consolidated Version
All routes in one file to bypass blueprint registration issues
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os
import sys
import sqlite3
import json

def create_app():
    """Create Flask application with all routes consolidated"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'magsasa-card-secret-key-2025')
    app.config['DATABASE_PATH'] = 'src/database/dynamic_pricing.db'
    
    # Enable CORS
    CORS(app)
    
    print("🚀 Starting MAGSASA-CARD Enhanced Platform API (Consolidated)")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version}")
    
    # Root endpoint
    @app.route('/')
    def api_info():
        """API information and available endpoints"""
        return jsonify({
            "api_name": "MAGSASA-CARD Enhanced Platform API",
            "version": "2.1.0",
            "description": "Agricultural Intelligence and Dynamic Pricing System with KaAni AI Integration",
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "deployment_info": {
                "architecture": "consolidated_routes",
                "blueprint_used": False,
                "total_routes": len(list(app.url_map.iter_rules())),
                "working_directory": os.getcwd(),
                "python_version": sys.version
            },
            "features": [
                "Dynamic Pricing Engine",
                "Logistics Integration", 
                "Order Processing",
                "Bulk Discounts",
                "CARD Member Benefits",
                "Market Comparison",
                "Pricing Analytics",
                "KaAni Agricultural Diagnosis",
                "AgScore Risk Assessment",
                "AI Product Recommendations"
            ],
            "endpoints": {
                "system": {
                    "health": "/health",
                    "api_health": "/api/health",
                    "status": "/api/status",
                    "info": "/"
                },
                "pricing": {
                    "health": "/api/pricing/health",
                    "inputs": "/api/pricing/inputs/<input_id>",
                    "calculate": "/api/pricing/calculate-order"
                },
                "kaani": {
                    "health": "/api/kaani/health",
                    "quick_diagnosis": "/api/kaani/quick-diagnosis"
                },
                "debug": {
                    "files": "/debug/files",
                    "routes": "/debug/routes"
                }
            }
        })
    
    # Health endpoints
    @app.route('/health')
    @app.route('/api/health')
    @app.route('/api/status')
    def health_check():
        """Comprehensive health check"""
        try:
            # Test database connection
            db_status = "connected"
            try:
                if os.path.exists(app.config['DATABASE_PATH']):
                    conn = sqlite3.connect(app.config['DATABASE_PATH'])
                    conn.execute('SELECT 1')
                    conn.close()
                else:
                    db_status = "database_file_missing"
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            return jsonify({
                "service": "MAGSASA-CARD AgriTech Platform",
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.1.0",
                "uptime": "running",
                "components": {
                    "database": db_status,
                    "ai_services": {
                        "openai": "available" if os.environ.get('OPENAI_API_KEY') else "not_configured"
                    },
                    "environment": {
                        "ENVIRONMENT": os.environ.get('ENVIRONMENT', 'development'),
                        "PORT": os.environ.get('PORT', '5000'),
                        "OPENAI_API_KEY": "set" if os.environ.get('OPENAI_API_KEY') else "not_set",
                        "GOOGLE_AI_API_KEY": "set" if os.environ.get('GOOGLE_AI_API_KEY') else "not_set"
                    }
                },
                "features": [
                    "Dynamic Pricing Engine",
                    "Agricultural Intelligence", 
                    "KaAni AI Integration",
                    "AgScore Risk Assessment"
                ]
            })
        except Exception as e:
            return jsonify({
                "service": "MAGSASA-CARD AgriTech Platform",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }), 500
    
    # Pricing endpoints
    @app.route('/api/pricing/health')
    def pricing_health():
        """Pricing service health check"""
        return jsonify({
            "service": "Dynamic Pricing Engine",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "features": [
                "Market-based pricing",
                "Bulk discount tiers",
                "CARD member benefits",
                "Real-time calculations"
            ],
            "pricing_tiers": {
                "retail": "Standard market price",
                "bulk": "Volume-based discounts",
                "card_member": "15% discount for CARD members",
                "premium": "Priority processing"
            }
        })
    
    @app.route('/api/pricing/inputs/<input_id>')
    def get_pricing_data(input_id):
        """Get pricing data for specific input"""
        # Mock pricing data
        pricing_data = {
            "fertilizer_001": {
                "name": "NPK Fertilizer 14-14-14",
                "category": "Fertilizer",
                "retail_price": 1250.00,
                "bulk_price": 1125.00,
                "card_member_price": 1062.50,
                "unit": "50kg bag",
                "availability": "In Stock"
            },
            "seed_001": {
                "name": "Hybrid Rice Seeds IR64",
                "category": "Seeds",
                "retail_price": 850.00,
                "bulk_price": 765.00,
                "card_member_price": 722.50,
                "unit": "20kg bag",
                "availability": "In Stock"
            }
        }
        
        if input_id in pricing_data:
            return jsonify({
                "input_id": input_id,
                "timestamp": datetime.utcnow().isoformat(),
                "pricing": pricing_data[input_id]
            })
        else:
            return jsonify({
                "input_id": input_id,
                "timestamp": datetime.utcnow().isoformat(),
                "pricing": {
                    "name": f"Agricultural Input {input_id}",
                    "category": "General",
                    "retail_price": 1000.00,
                    "bulk_price": 900.00,
                    "card_member_price": 850.00,
                    "unit": "per unit",
                    "availability": "Available"
                }
            })
    
    @app.route('/api/pricing/calculate-order', methods=['POST'])
    def calculate_order():
        """Calculate order total with discounts"""
        try:
            data = request.get_json() or {}
            items = data.get('items', [])
            customer_type = data.get('customer_type', 'retail')
            
            total = 0
            calculated_items = []
            
            for item in items:
                quantity = item.get('quantity', 1)
                base_price = item.get('price', 1000.00)
                
                # Apply discounts based on customer type
                if customer_type == 'card_member':
                    final_price = base_price * 0.85  # 15% discount
                elif customer_type == 'bulk' and quantity >= 10:
                    final_price = base_price * 0.90  # 10% bulk discount
                else:
                    final_price = base_price
                
                item_total = final_price * quantity
                total += item_total
                
                calculated_items.append({
                    "name": item.get('name', 'Agricultural Input'),
                    "quantity": quantity,
                    "base_price": base_price,
                    "final_price": final_price,
                    "item_total": item_total
                })
            
            return jsonify({
                "timestamp": datetime.utcnow().isoformat(),
                "customer_type": customer_type,
                "items": calculated_items,
                "subtotal": total,
                "total": total,
                "savings": sum(item.get('price', 1000) * item.get('quantity', 1) for item in items) - total
            })
            
        except Exception as e:
            return jsonify({
                "error": "Calculation failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 400
    
    # KaAni AI endpoints
    @app.route('/api/kaani/health')
    def kaani_health():
        """KaAni AI service health check"""
        return jsonify({
            "service": "KaAni Agricultural Intelligence",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "ai_providers": {
                "openai": bool(os.environ.get('OPENAI_API_KEY')),
                "google_ai": bool(os.environ.get('GOOGLE_AI_API_KEY'))
            },
            "features": [
                "Crop disease diagnosis",
                "Pest identification",
                "Soil analysis recommendations",
                "Weather-based guidance",
                "Product recommendations"
            ],
            "supported_languages": ["English", "Filipino", "Tagalog"]
        })
    
    @app.route('/api/kaani/quick-diagnosis', methods=['POST'])
    def quick_diagnosis():
        """Quick agricultural diagnosis"""
        try:
            data = request.get_json() or {}
            symptoms = data.get('symptoms', '')
            crop_type = data.get('crop_type', 'rice')
            
            # Mock AI response (in production, this would call OpenAI)
            diagnosis = {
                "diagnosis_id": f"diag_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "crop_type": crop_type,
                "symptoms_analyzed": symptoms,
                "likely_issues": [
                    {
                        "issue": "Nutrient Deficiency",
                        "confidence": 0.75,
                        "description": "Signs indicate possible nitrogen deficiency"
                    },
                    {
                        "issue": "Pest Damage", 
                        "confidence": 0.60,
                        "description": "Leaf damage patterns suggest insect activity"
                    }
                ],
                "recommendations": [
                    "Apply balanced NPK fertilizer",
                    "Monitor for pest activity",
                    "Ensure proper irrigation"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return jsonify(diagnosis)
            
        except Exception as e:
            return jsonify({
                "error": "Diagnosis failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 400
    
    # Debug endpoints
    @app.route('/debug/files')
    def debug_files():
        """Check file structure"""
        try:
            current_dir = os.getcwd()
            file_structure = {
                "current_directory": current_dir,
                "current_files": os.listdir(current_dir) if os.path.exists(current_dir) else [],
                "src_directory": {
                    "exists": os.path.exists(os.path.join(current_dir, 'src')),
                    "files": os.listdir(os.path.join(current_dir, 'src')) if os.path.exists(os.path.join(current_dir, 'src')) else []
                },
                "routes_directory": {
                    "exists": os.path.exists(os.path.join(current_dir, 'src', 'routes')),
                    "files": os.listdir(os.path.join(current_dir, 'src', 'routes')) if os.path.exists(os.path.join(current_dir, 'src', 'routes')) else []
                }
            }
            return jsonify(file_structure)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/debug/routes')
    def debug_routes():
        """List all registered routes"""
        try:
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    "endpoint": rule.endpoint,
                    "methods": list(rule.methods),
                    "rule": rule.rule
                })
            
            return jsonify({
                "total_routes": len(routes),
                "routes": sorted(routes, key=lambda x: x['rule']),
                "app_info": {
                    "name": app.name,
                    "debug": app.debug,
                    "testing": app.testing
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # Error handlers
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
    
    print(f"✅ Consolidated app created with {len(list(app.url_map.iter_rules()))} routes")
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
