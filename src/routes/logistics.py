from flask import Blueprint, jsonify, request
from ..database.connection import get_db_connection

logistics_bp = Blueprint('logistics', __name__)

@logistics_bp.route('/api/logistics/options', methods=['GET'])
def get_logistics_options():
    """Get all available logistics/delivery options"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM logistics_options 
            ORDER BY estimated_days, base_cost
        ''')
        
        options = []
        for row in cursor.fetchall():
            option = {
                'id': row['id'],
                'name': row['name'],
                'base_cost': row['base_cost'],
                'cost_per_km': row['cost_per_km'],
                'estimated_days': row['estimated_days'],
                'description': row['description']
            }
            options.append(option)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': options,
            'total': len(options)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@logistics_bp.route('/api/logistics/calculate', methods=['POST'])
def calculate_logistics_cost():
    """Calculate logistics cost based on distance and option"""
    try:
        data = request.get_json()
        option_id = data.get('option_id')
        distance = data.get('distance', 0)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM logistics_options WHERE id = ?', (option_id,))
        option = cursor.fetchone()
        
        if not option:
            return jsonify({
                'success': False,
                'error': 'Logistics option not found'
            }), 404
        
        total_cost = option['base_cost'] + (option['cost_per_km'] * distance)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'option_id': option['id'],
                'option_name': option['name'],
                'distance': distance,
                'base_cost': option['base_cost'],
                'distance_cost': option['cost_per_km'] * distance,
                'total_cost': total_cost,
                'estimated_days': option['estimated_days']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@logistics_bp.route('/api/logistics/estimate', methods=['POST'])
def estimate_delivery():
    """Estimate delivery time and cost for multiple options"""
    try:
        data = request.get_json()
        distance = data.get('distance', 0)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM logistics_options ORDER BY estimated_days')
        options = cursor.fetchall()
        
        estimates = []
        for option in options:
            total_cost = option['base_cost'] + (option['cost_per_km'] * distance)
            
            estimate = {
                'option_id': option['id'],
                'name': option['name'],
                'total_cost': total_cost,
                'estimated_days': option['estimated_days'],
                'description': option['description']
            }
            estimates.append(estimate)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': estimates,
            'distance': distance
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
