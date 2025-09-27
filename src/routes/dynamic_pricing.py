from flask import Blueprint, jsonify, request
from ..database.connection import get_db_connection

dynamic_pricing_bp = Blueprint('dynamic_pricing', __name__)

@dynamic_pricing_bp.route('/api/pricing/inputs', methods=['GET'])
def get_pricing_inputs():
    """Get all agricultural inputs with pricing information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ai.*, 
                   GROUP_CONCAT(
                       pt.min_quantity || '-' || 
                       COALESCE(pt.max_quantity, 'unlimited') || ':' || 
                       pt.discount_percentage || '%'
                   ) as pricing_tiers
            FROM agricultural_inputs ai
            LEFT JOIN pricing_tiers pt ON ai.id = pt.input_id
            GROUP BY ai.id
            ORDER BY ai.category, ai.name
        ''')
        
        inputs = []
        for row in cursor.fetchall():
            input_data = {
                'id': row['id'],
                'name': row['name'],
                'category': row['category'],
                'base_price': row['base_price'],
                'unit': row['unit'],
                'description': row['description'],
                'pricing_tiers': row['pricing_tiers'].split(',') if row['pricing_tiers'] else []
            }
            inputs.append(input_data)
        
        conn.close()
        return jsonify({
            'success': True,
            'data': inputs,
            'total': len(inputs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dynamic_pricing_bp.route('/api/pricing/inputs/<int:input_id>', methods=['GET'])
def get_pricing_input_details(input_id):
    """Get detailed pricing information for a specific input"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get input details
        cursor.execute('SELECT * FROM agricultural_inputs WHERE id = ?', (input_id,))
        input_data = cursor.fetchone()
        
        if not input_data:
            return jsonify({
                'success': False,
                'error': 'Input not found'
            }), 404
        
        # Get pricing tiers
        cursor.execute('''
            SELECT * FROM pricing_tiers 
            WHERE input_id = ? 
            ORDER BY min_quantity
        ''', (input_id,))
        pricing_tiers = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'id': input_data['id'],
                'name': input_data['name'],
                'category': input_data['category'],
                'base_price': input_data['base_price'],
                'unit': input_data['unit'],
                'description': input_data['description'],
                'pricing_tiers': [
                    {
                        'min_quantity': tier['min_quantity'],
                        'max_quantity': tier['max_quantity'],
                        'discount_percentage': tier['discount_percentage']
                    } for tier in pricing_tiers
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dynamic_pricing_bp.route('/api/pricing/calculate', methods=['POST'])
def calculate_pricing():
    """Calculate total pricing for an order with dynamic pricing"""
    try:
        data = request.get_json()
        items = data.get('items', [])
        is_card_member = data.get('is_card_member', False)
        delivery_distance = data.get('delivery_distance', 0)
        logistics_option_id = data.get('logistics_option_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_amount = 0
        total_savings = 0
        order_items = []
        
        for item in items:
            input_id = item['input_id']
            quantity = item['quantity']
            
            # Get input details
            cursor.execute('SELECT * FROM agricultural_inputs WHERE id = ?', (input_id,))
            input_data = cursor.fetchone()
            
            if not input_data:
                continue
            
            base_price = input_data['base_price']
            
            # Calculate bulk discount
            cursor.execute('''
                SELECT discount_percentage FROM pricing_tiers 
                WHERE input_id = ? AND min_quantity <= ? 
                AND (max_quantity IS NULL OR max_quantity >= ?)
                ORDER BY min_quantity DESC LIMIT 1
            ''', (input_id, quantity, quantity))
            
            tier_result = cursor.fetchone()
            bulk_discount = tier_result['discount_percentage'] if tier_result else 0
            
            # Calculate item pricing
            subtotal = base_price * quantity
            bulk_discount_amount = subtotal * (bulk_discount / 100)
            card_discount_amount = 0
            
            if is_card_member:
                card_discount_amount = subtotal * 0.03  # 3% CARD member discount
            
            total_discount = bulk_discount_amount + card_discount_amount
            item_total = subtotal - total_discount
            
            order_items.append({
                'input_id': input_id,
                'name': input_data['name'],
                'quantity': quantity,
                'unit': input_data['unit'],
                'base_price': base_price,
                'subtotal': subtotal,
                'bulk_discount': bulk_discount,
                'bulk_discount_amount': bulk_discount_amount,
                'card_discount_amount': card_discount_amount,
                'total_discount': total_discount,
                'item_total': item_total
            })
            
            total_amount += item_total
            total_savings += total_discount
        
        # Calculate logistics cost
        cursor.execute('SELECT * FROM logistics_options WHERE id = ?', (logistics_option_id,))
        logistics = cursor.fetchone()
        
        logistics_cost = 0
        if logistics:
            logistics_cost = logistics['base_cost'] + (logistics['cost_per_km'] * delivery_distance)
        
        final_total = total_amount + logistics_cost
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'items': order_items,
                'subtotal': total_amount,
                'total_savings': total_savings,
                'logistics_cost': logistics_cost,
                'delivery_distance': delivery_distance,
                'final_total': final_total,
                'is_card_member': is_card_member,
                'logistics_option': {
                    'id': logistics['id'],
                    'name': logistics['name'],
                    'estimated_days': logistics['estimated_days']
                } if logistics else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dynamic_pricing_bp.route('/api/market-comparison', methods=['GET'])
def get_market_comparison():
    """Get market price comparison data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ai.*, 
                   (ai.base_price * 1.15) as market_price,
                   (ai.base_price * 0.15) as potential_savings
            FROM agricultural_inputs ai
            ORDER BY ai.category, ai.name
        ''')
        
        comparisons = []
        for row in cursor.fetchall():
            comparison = {
                'id': row['id'],
                'name': row['name'],
                'category': row['category'],
                'magsasa_price': row['base_price'],
                'market_price': row['market_price'],
                'savings': row['potential_savings'],
                'savings_percentage': 15.0,
                'unit': row['unit']
            }
            comparisons.append(comparison)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': comparisons,
            'total': len(comparisons)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
