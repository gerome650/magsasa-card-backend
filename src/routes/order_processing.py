#!/usr/bin/env python3
"""
Order Processing API Endpoints
MAGSASA-CARD Enhanced Platform

Handles order creation, processing, and tracking with dynamic pricing
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta
import sqlite3
import json
import uuid
import random

order_processing_bp = Blueprint('order_processing', __name__)

# Database connection helper
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('src/database/dynamic_pricing.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_transaction_code():
    """Generate unique transaction code"""
    return f"TXN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def generate_delivery_code():
    """Generate unique delivery code"""
    return f"DEL-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

@order_processing_bp.route('/api/orders/create', methods=['POST'])
def create_order():
    """
    Create a new order with dynamic pricing
    
    Expected JSON payload:
    {
        "farmer_id": 1,
        "items": [
            {"input_id": 1, "quantity": 10},
            {"input_id": 2, "quantity": 5}
        ],
        "delivery_option": "platform_logistics",
        "logistics_provider_id": 1,
        "delivery_address": "Barangay San Jose, Laguna",
        "delivery_coordinates": "14.1694,121.2441",
        "card_member": true,
        "card_member_id": "CARD-12345",
        "express_delivery": false,
        "payment_method": "card_auto_debit",
        "notes": "Please deliver in the morning"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'items' not in data:
            return jsonify({'error': 'Items are required'}), 400
        
        conn = get_db_connection()
        
        # Generate transaction code
        transaction_code = generate_transaction_code()
        
        # Calculate order totals (reuse logic from calculate_order_total)
        subtotal_wholesale = 0.0
        subtotal_retail = 0.0
        platform_margin_total = 0.0
        items_breakdown = []
        
        # Process each item
        for item in data['items']:
            input_id = item['input_id']
            quantity = item['quantity']
            
            # Get input data
            input_data = conn.execute('''
                SELECT * FROM agricultural_inputs WHERE id = ? AND is_active = 1
            ''', (input_id,)).fetchone()
            
            if not input_data:
                return jsonify({'error': f'Input {input_id} not found'}), 404
            
            # Check stock availability
            if input_data['current_stock'] < quantity:
                return jsonify({'error': f'Insufficient stock for {input_data["name"]}. Available: {input_data["current_stock"]}, Requested: {quantity}'}), 400
            
            # Calculate bulk pricing
            unit_price = input_data['retail_price']
            if quantity >= input_data['bulk_tier_3_quantity'] and input_data['bulk_tier_3_price']:
                unit_price = input_data['bulk_tier_3_price']
            elif quantity >= input_data['bulk_tier_2_quantity'] and input_data['bulk_tier_2_price']:
                unit_price = input_data['bulk_tier_2_price']
            elif quantity >= input_data['bulk_tier_1_quantity'] and input_data['bulk_tier_1_price']:
                unit_price = input_data['bulk_tier_1_price']
            
            wholesale_unit_price = input_data['wholesale_price']
            
            # Calculate totals for this item
            item_wholesale_total = wholesale_unit_price * quantity
            item_retail_total = unit_price * quantity
            item_margin = item_retail_total - item_wholesale_total
            
            # Add to overall totals
            subtotal_wholesale += item_wholesale_total
            subtotal_retail += item_retail_total
            platform_margin_total += item_margin
            
            items_breakdown.append({
                'input_id': input_id,
                'name': input_data['name'],
                'quantity': quantity,
                'unit_price': unit_price,
                'wholesale_unit_price': wholesale_unit_price,
                'total_price': item_retail_total,
                'wholesale_total': item_wholesale_total,
                'platform_margin': item_margin
            })
        
        # Calculate delivery costs
        delivery_fee = 0.0
        logistics_provider_fee = 0.0
        platform_logistics_margin = 0.0
        delivery_option = data.get('delivery_option', 'farmer_pickup')
        logistics_provider_id = data.get('logistics_provider_id')
        
        if delivery_option == 'platform_logistics' and logistics_provider_id:
            logistics_data = conn.execute('''
                SELECT * FROM logistics_options WHERE id = ? AND is_active = 1
            ''', (logistics_provider_id,)).fetchone()
            
            if logistics_data:
                base_fee = logistics_data['base_delivery_fee']
                free_threshold = logistics_data['free_delivery_threshold']
                express_surcharge = logistics_data['express_delivery_surcharge'] if data.get('express_delivery') else 0
                
                if subtotal_retail >= free_threshold:
                    delivery_fee = express_surcharge
                else:
                    delivery_fee = base_fee + express_surcharge
                
                logistics_provider_fee = delivery_fee * 0.8
                platform_logistics_margin = delivery_fee * 0.2
        
        elif delivery_option == 'supplier_delivery':
            delivery_fee = 75.0  # Average supplier delivery fee
            logistics_provider_fee = delivery_fee
        
        elif delivery_option == 'farmer_pickup':
            # Apply pickup discount
            pickup_discount = subtotal_retail * 0.02
            subtotal_retail -= pickup_discount
        
        # Apply CARD member discount
        card_member_discount = 0.0
        if data.get('card_member'):
            card_member_discount = subtotal_retail * 0.03
        
        # Calculate final totals
        total_amount = subtotal_retail + delivery_fee - card_member_discount
        total_platform_revenue = platform_margin_total + platform_logistics_margin
        
        # Create transaction record
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO input_transactions (
                farmer_id, transaction_code, transaction_date, items,
                subtotal_wholesale, subtotal_retail, platform_margin_total,
                delivery_fee, logistics_provider_fee, platform_logistics_margin,
                card_member_discount, total_amount, total_platform_revenue,
                delivery_type, delivery_address, delivery_coordinates,
                logistics_option_id, payment_method, card_member_id,
                status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('farmer_id'),
            transaction_code,
            datetime.utcnow(),
            json.dumps(items_breakdown),
            subtotal_wholesale,
            subtotal_retail,
            platform_margin_total,
            delivery_fee,
            logistics_provider_fee,
            platform_logistics_margin,
            card_member_discount,
            total_amount,
            total_platform_revenue,
            delivery_option,
            data.get('delivery_address'),
            data.get('delivery_coordinates'),
            logistics_provider_id,
            data.get('payment_method', 'card_auto_debit'),
            data.get('card_member_id'),
            'pending',
            data.get('notes')
        ))
        
        transaction_id = cursor.lastrowid
        
        # Update stock levels
        for item in data['items']:
            conn.execute('''
                UPDATE agricultural_inputs 
                SET current_stock = current_stock - ?
                WHERE id = ?
            ''', (item['quantity'], item['input_id']))
        
        # Create delivery order if needed
        delivery_order_id = None
        if delivery_option in ['platform_logistics', 'supplier_delivery']:
            delivery_code = generate_delivery_code()
            
            # Calculate delivery dates
            delivery_days = 2  # Default
            if logistics_provider_id:
                logistics_data = conn.execute('''
                    SELECT standard_delivery_days, express_delivery_days FROM logistics_options WHERE id = ?
                ''', (logistics_provider_id,)).fetchone()
                if logistics_data:
                    delivery_days = logistics_data['express_delivery_days'] if data.get('express_delivery') else logistics_data['standard_delivery_days']
            
            scheduled_delivery_date = datetime.utcnow() + timedelta(days=delivery_days)
            
            cursor.execute('''
                INSERT INTO delivery_orders (
                    transaction_id, logistics_option_id, delivery_code,
                    pickup_address, delivery_address, scheduled_delivery_date,
                    current_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id,
                logistics_provider_id,
                delivery_code,
                'CARD MRI Center, Laguna',  # Default pickup location
                data.get('delivery_address'),
                scheduled_delivery_date,
                'pending'
            ))
            
            delivery_order_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Prepare response
        response = {
            'success': True,
            'transaction_id': transaction_id,
            'transaction_code': transaction_code,
            'order_summary': {
                'total_items': len(data['items']),
                'subtotal_retail': round(subtotal_retail, 2),
                'delivery_fee': round(delivery_fee, 2),
                'card_member_discount': round(card_member_discount, 2),
                'total_amount': round(total_amount, 2),
                'platform_revenue': round(total_platform_revenue, 2)
            },
            'delivery_info': {
                'delivery_option': delivery_option,
                'delivery_order_id': delivery_order_id,
                'estimated_delivery_days': delivery_days if delivery_option != 'farmer_pickup' else 0
            },
            'payment_info': {
                'payment_method': data.get('payment_method', 'card_auto_debit'),
                'card_member': data.get('card_member', False),
                'auto_debit_reference': f"CARD-{transaction_code}" if data.get('card_member') else None
            }
        }
        
        return jsonify(response), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_processing_bp.route('/api/orders/<int:transaction_id>', methods=['GET'])
def get_order_details(transaction_id):
    """Get detailed order information"""
    try:
        conn = get_db_connection()
        
        # Get transaction details
        transaction = conn.execute('''
            SELECT * FROM input_transactions WHERE id = ?
        ''', (transaction_id,)).fetchone()
        
        if not transaction:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get delivery order if exists
        delivery_order = conn.execute('''
            SELECT * FROM delivery_orders WHERE transaction_id = ?
        ''', (transaction_id,)).fetchone()
        
        # Parse items
        items = json.loads(transaction['items']) if transaction['items'] else []
        
        # Get logistics provider info if applicable
        logistics_info = None
        if transaction['logistics_option_id']:
            logistics_data = conn.execute('''
                SELECT provider_name, provider_type FROM logistics_options WHERE id = ?
            ''', (transaction['logistics_option_id'],)).fetchone()
            if logistics_data:
                logistics_info = {
                    'provider_name': logistics_data['provider_name'],
                    'provider_type': logistics_data['provider_type']
                }
        
        response = {
            'transaction_id': transaction['id'],
            'transaction_code': transaction['transaction_code'],
            'transaction_date': transaction['transaction_date'],
            'farmer_id': transaction['farmer_id'],
            'status': transaction['status'],
            
            'order_details': {
                'items': items,
                'subtotal_wholesale': transaction['subtotal_wholesale'],
                'subtotal_retail': transaction['subtotal_retail'],
                'platform_margin_total': transaction['platform_margin_total'],
                'delivery_fee': transaction['delivery_fee'],
                'card_member_discount': transaction['card_member_discount'],
                'total_amount': transaction['total_amount']
            },
            
            'delivery_info': {
                'delivery_type': transaction['delivery_type'],
                'delivery_address': transaction['delivery_address'],
                'delivery_status': transaction['delivery_status'],
                'logistics_provider': logistics_info
            },
            
            'payment_info': {
                'payment_method': transaction['payment_method'],
                'payment_status': transaction['payment_status'],
                'payment_date': transaction['payment_date'],
                'card_member_id': transaction['card_member_id'],
                'auto_debit_reference': transaction['auto_debit_reference']
            },
            
            'delivery_order': {
                'delivery_code': delivery_order['delivery_code'] if delivery_order else None,
                'scheduled_delivery_date': delivery_order['scheduled_delivery_date'] if delivery_order else None,
                'current_status': delivery_order['current_status'] if delivery_order else None,
                'tracking_available': delivery_order is not None
            } if delivery_order else None,
            
            'notes': transaction['notes']
        }
        
        conn.close()
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_processing_bp.route('/api/orders/<int:transaction_id>/status', methods=['PUT'])
def update_order_status(transaction_id):
    """
    Update order status
    
    Expected JSON payload:
    {
        "status": "confirmed",
        "payment_status": "completed",
        "notes": "Payment confirmed via CARD auto-debit"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        conn = get_db_connection()
        
        # Check if transaction exists
        transaction = conn.execute('''
            SELECT id FROM input_transactions WHERE id = ?
        ''', (transaction_id,)).fetchone()
        
        if not transaction:
            return jsonify({'error': 'Order not found'}), 404
        
        # Update transaction
        update_fields = ['status = ?']
        params = [data['status']]
        
        if 'payment_status' in data:
            update_fields.append('payment_status = ?')
            params.append(data['payment_status'])
            
            if data['payment_status'] == 'completed':
                update_fields.append('payment_date = ?')
                params.append(datetime.utcnow())
        
        if 'notes' in data:
            update_fields.append('notes = ?')
            params.append(data['notes'])
        
        update_fields.append('updated_at = ?')
        params.append(datetime.utcnow())
        params.append(transaction_id)
        
        conn.execute(f'''
            UPDATE input_transactions 
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', params)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'updated_status': data['status'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_processing_bp.route('/api/orders/farmer/<int:farmer_id>', methods=['GET'])
def get_farmer_orders(farmer_id):
    """Get all orders for a specific farmer"""
    try:
        conn = get_db_connection()
        
        # Get query parameters
        status = request.args.get('status')
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = 'SELECT * FROM input_transactions WHERE farmer_id = ?'
        params = [farmer_id]
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        query += ' ORDER BY transaction_date DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        transactions = conn.execute(query, params).fetchall()
        
        orders = []
        for transaction in transactions:
            items = json.loads(transaction['items']) if transaction['items'] else []
            
            orders.append({
                'transaction_id': transaction['id'],
                'transaction_code': transaction['transaction_code'],
                'transaction_date': transaction['transaction_date'],
                'status': transaction['status'],
                'total_amount': transaction['total_amount'],
                'delivery_type': transaction['delivery_type'],
                'delivery_status': transaction['delivery_status'],
                'payment_status': transaction['payment_status'],
                'item_count': len(items),
                'items_summary': [{'name': item['name'], 'quantity': item['quantity']} for item in items[:3]]  # First 3 items
            })
        
        # Get total count
        total_count = conn.execute('''
            SELECT COUNT(*) FROM input_transactions WHERE farmer_id = ?
        ''', (farmer_id,)).fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'farmer_id': farmer_id,
            'orders': orders,
            'pagination': {
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_processing_bp.route('/api/orders/stats', methods=['GET'])
def get_order_statistics():
    """Get order statistics and analytics"""
    try:
        conn = get_db_connection()
        
        # Get date range
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Order statistics
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                SUM(total_platform_revenue) as total_platform_revenue,
                AVG(total_amount) as avg_order_value,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders
            FROM input_transactions
            WHERE DATE(transaction_date) BETWEEN ? AND ?
        ''', (start_date, end_date)).fetchone()
        
        # Delivery type breakdown
        delivery_stats = conn.execute('''
            SELECT 
                delivery_type,
                COUNT(*) as count,
                SUM(total_amount) as revenue
            FROM input_transactions
            WHERE DATE(transaction_date) BETWEEN ? AND ?
            GROUP BY delivery_type
        ''', (start_date, end_date)).fetchall()
        
        # Top selling inputs
        top_inputs = conn.execute('''
            SELECT 
                ai.name,
                ai.category,
                COUNT(*) as order_count,
                SUM(JSON_EXTRACT(it.items, '$[*].quantity')) as total_quantity
            FROM input_transactions it
            JOIN agricultural_inputs ai ON JSON_EXTRACT(it.items, '$[0].input_id') = ai.id
            WHERE DATE(it.transaction_date) BETWEEN ? AND ?
            GROUP BY ai.id, ai.name, ai.category
            ORDER BY total_quantity DESC
            LIMIT 10
        ''', (start_date, end_date)).fetchall()
        
        conn.close()
        
        return jsonify({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'order_statistics': {
                'total_orders': stats['total_orders'],
                'total_revenue': round(stats['total_revenue'] or 0, 2),
                'total_platform_revenue': round(stats['total_platform_revenue'] or 0, 2),
                'avg_order_value': round(stats['avg_order_value'] or 0, 2),
                'completed_orders': stats['completed_orders'],
                'pending_orders': stats['pending_orders'],
                'cancelled_orders': stats['cancelled_orders'],
                'completion_rate': round((stats['completed_orders'] / stats['total_orders']) * 100, 2) if stats['total_orders'] > 0 else 0
            },
            'delivery_breakdown': [
                {
                    'delivery_type': row['delivery_type'],
                    'order_count': row['count'],
                    'revenue': round(row['revenue'], 2)
                } for row in delivery_stats
            ],
            'top_inputs': [
                {
                    'name': row['name'],
                    'category': row['category'],
                    'order_count': row['order_count'],
                    'total_quantity': row['total_quantity']
                } for row in top_inputs
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@order_processing_bp.route('/api/orders/health', methods=['GET'])
def orders_health_check():
    """Health check for order processing API"""
    try:
        conn = get_db_connection()
        
        # Check database connectivity
        total_orders = conn.execute('SELECT COUNT(*) FROM input_transactions').fetchone()[0]
        pending_orders = conn.execute('SELECT COUNT(*) FROM input_transactions WHERE status = "pending"').fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'features': [
                'order_creation',
                'dynamic_pricing',
                'bulk_discounts',
                'logistics_integration',
                'card_member_benefits',
                'order_tracking',
                'payment_processing'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
