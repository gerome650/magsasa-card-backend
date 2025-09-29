from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MAGSASA-CARD AgriTech Platform",
        "version": "2.1.0"
    }), 200

@health_bp.route('/health', methods=['GET'])
def simple_health():
    return jsonify({"status": "ok"}), 200

