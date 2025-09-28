"""
Debug Routes - Direct route definitions for testing
This file contains direct route definitions to test if the issue is with blueprints or imports
"""

from flask import Flask, jsonify
from datetime import datetime
import os
import sys

def add_debug_routes(app):
    """Add debug routes directly to the app (not as blueprints)"""
    
    @app.route('/debug/health')
    def debug_health():
        """Direct health check route (not using blueprint)"""
        return jsonify({
            "service": "MAGSASA-CARD AgriTech Platform",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "debug_info": {
                "route_type": "direct_route",
                "blueprint_used": False,
                "working_directory": os.getcwd(),
                "python_path": sys.path[:3],  # First 3 entries
                "src_exists": os.path.exists('src'),
                "routes_exists": os.path.exists('src/routes') if os.path.exists('src') else False
            }
        })
    
    @app.route('/debug/pricing')
    def debug_pricing():
        """Direct pricing route (not using blueprint)"""
        return jsonify({
            "service": "Dynamic Pricing Engine",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "debug_info": {
                "route_type": "direct_route",
                "blueprint_used": False,
                "mock_pricing": {
                    "fertilizer_001": {
                        "name": "NPK Fertilizer 14-14-14",
                        "retail_price": 1250.00,
                        "card_member_price": 1125.00
                    }
                }
            }
        })
    
    @app.route('/debug/kaani')
    def debug_kaani():
        """Direct KaAni route (not using blueprint)"""
        return jsonify({
            "service": "KaAni Agricultural Intelligence",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "debug_info": {
                "route_type": "direct_route",
                "blueprint_used": False,
                "ai_providers": {
                    "openai": bool(os.environ.get('OPENAI_API_KEY')),
                    "google_ai": bool(os.environ.get('GOOGLE_AI_API_KEY'))
                }
            }
        })
    
    @app.route('/debug/routes')
    def debug_routes():
        """List all registered routes"""
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
            "blueprints": list(app.blueprints.keys()),
            "debug_info": {
                "app_name": app.name,
                "config_keys": list(app.config.keys()),
                "blueprint_status": app.config.get('BLUEPRINT_STATUS', {})
            }
        })
    
    @app.route('/debug/files')
    def debug_files():
        """Check file structure"""
        file_structure = {}
        
        # Check current directory
        current_dir = os.getcwd()
        file_structure['current_directory'] = current_dir
        file_structure['current_files'] = os.listdir(current_dir) if os.path.exists(current_dir) else []
        
        # Check src directory
        src_dir = os.path.join(current_dir, 'src')
        file_structure['src_directory'] = {
            'exists': os.path.exists(src_dir),
            'files': os.listdir(src_dir) if os.path.exists(src_dir) else []
        }
        
        # Check routes directory
        routes_dir = os.path.join(src_dir, 'routes')
        file_structure['routes_directory'] = {
            'exists': os.path.exists(routes_dir),
            'files': os.listdir(routes_dir) if os.path.exists(routes_dir) else []
        }
        
        # Check individual route files
        route_files = ['health.py', 'api.py', 'dynamic_pricing.py', 'kaani_routes.py']
        file_structure['route_files'] = {}
        
        for route_file in route_files:
            file_path = os.path.join(routes_dir, route_file)
            file_structure['route_files'][route_file] = {
                'exists': os.path.exists(file_path),
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
        
        return jsonify(file_structure)
    
    print("✅ Debug routes added successfully")
    return app
