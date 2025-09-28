"""
Health Check API Endpoints
MAGSASA-CARD Enhanced Platform

Provides health check and status monitoring endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime
import os
import sys

health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Main health check endpoint"""
    try:
        # Check database connectivity
        db_status = "connected"
        try:
            import sqlite3
            conn = sqlite3.connect('src/database/dynamic_pricing.db')
            conn.execute('SELECT 1')
            conn.close()
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Check AI services
        ai_services = {}
        
        # Check OpenAI
        try:
            import openai
            ai_services["openai"] = "available"
        except ImportError:
            ai_services["openai"] = "not_installed"
        except Exception as e:
            ai_services["openai"] = f"error: {str(e)}"
        
        # Check environment variables
        env_status = {
            "OPENAI_API_KEY": "set" if os.environ.get('OPENAI_API_KEY') else "not_set",
            "GOOGLE_AI_API_KEY": "set" if os.environ.get('GOOGLE_AI_API_KEY') else "not_set",
            "ENVIRONMENT": os.environ.get('ENVIRONMENT', 'development'),
            "PORT": os.environ.get('PORT', '5000')
        }
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "MAGSASA-CARD AgriTech Platform",
            "version": "2.1.0",
            "components": {
                "database": db_status,
                "ai_services": ai_services,
                "environment": env_status
            },
            "uptime": "running",
            "features": [
                "Dynamic Pricing Engine",
                "Agricultural Intelligence",
                "KaAni AI Integration",
                "AgScore Risk Assessment"
            ]
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "service": "MAGSASA-CARD AgriTech Platform"
        }), 500

@health_bp.route('/api/status', methods=['GET'])
def status_check():
    """Detailed status endpoint"""
    try:
        # System information
        system_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd(),
            "environment_variables": len(os.environ),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check available modules
        available_modules = {}
        modules_to_check = ['flask', 'sqlite3', 'openai', 'requests', 'pandas']
        
        for module in modules_to_check:
            try:
                __import__(module)
                available_modules[module] = "available"
            except ImportError:
                available_modules[module] = "not_available"
        
        return jsonify({
            "service": "MAGSASA-CARD AgriTech Platform",
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_info,
            "modules": available_modules,
            "endpoints": {
                "health": "/api/health",
                "status": "/api/status",
                "pricing": "/api/pricing/*",
                "kaani": "/api/kaani/*"
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500

@health_bp.route('/health', methods=['GET'])
def simple_health():
    """Simple health check for load balancers"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }), 200
