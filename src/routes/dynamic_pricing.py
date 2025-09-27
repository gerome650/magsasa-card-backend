#!/usr/bin/env python3
"""
Dynamic Pricing API Endpoints
MAGSASA-CARD Enhanced Platform

Provides API endpoints for dynamic pricing, logistics options, and order calculations
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
import sqlite3
import json
import math

dynamic_pricing_bp = Blueprint('dynamic_pricing', __name__)

# Database connection helper
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('src/database/dynamic_pricing.db')
    conn.row_factory = sqlite3.Row
    return conn

# Utility functions
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    # Simplified distance calculation (Haversine formula)
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def get_bulk_price(input_data, quantity):
    """Calculate bulk pricing based on quantity"""
    base_price = input_data['retail_price']
    
    if quantity >= input_data['bulk_tier_3_quantity'] and input_data['bulk_tier_3_price']:
        return input_data['bulk_tier_3_price']
    elif quantity >= input_data['bulk_tier_2_quantity'] and input_data['bulk_tier_2_price']:
        return input_data['bulk_tier_2_price']
    elif quantity >= input_data['bulk_tier_1_quantity'] and input_data['bulk_tier_1_price']:
        return input_data['bulk_tier_1_price']
    else:
        return base_price

# API Endpoints

@dynamic_pricing_bp.route('/api/pricing/inputs/<int:input_id>', methods=['GET'])
def get_input_pricing(input_id):
    """
    Get comprehensive pricing information for a specific input
    
    Returns:
    - Wholesale and retail prices
    - Market comparison
    - Bulk pricing tiers
    - Available logistics options
    """
    try:
        conn = get_db_connection()
        
        # Get input pricing information
        input_data = conn.execute('''
            SELECT * FROM agricultural_inputs WHERE id = ? AND is_active = 1
        ''', (input_id,)).fetchone()
        
        if not input_data:
            return jsonify({'error': 'Input not found'}), 404
        
        # Calculate farmer savings
        market_price = input_data['market_retail_price'] or input_data['retail_price']
        farmer_savings = market_price - input_data['retail_price']
        savings_percentage = (farmer_savings / market_price) * 100 if market_price > 0 else 0
        
        # Get logistics options
        logistics_options = conn.execute('''
            SELECT * FROM logistics_options WHERE is_active = 1
        ''').fetchall()
        
        # Format logistics options
        logistics_formatted = []
        for option in logistics_options:
            logistics_formatted.append({
                'id': option['id'],
                'provider_name': option['provider_name'],
                'provider_type': option['provider_type'],
                'base_delivery_fee': option['base_delivery_fee'],
                'per_km_rate': option['per_km_rate'],
                'minimum_order_value': option['minimum_order_value'],
                'free_delivery_threshold': option['free_delivery_threshold'],
                'standard_delivery_days': option['standard_delivery_days'],
                'express_delivery_days': option['express_delivery_days'],
                'express_delivery_surcharge': option['express_delivery_surcharge'],
                'operating_hours': option['operating_hours']
            })
        
        response = {
            'input_id': input_data['id'],
            'name': input_data['name'],
            'category': input_data['category'],
            'brand': input_data['brand'],
            'package_size': input_data['package_size'],
            'unit_of_measure': input_data['unit_of_measure'],
            
            # Pricing Information
            'pricing': {
                'wholesale_price': input_data['wholesale_price'],
                'retail_price': input_data['retail_price'],
                'market_retail_price': market_price,
                'platform_margin': input_data['platform_margin'],
                'margin_percentage': input_data['margin_percentage'],
                'farmer_savings': farmer_savings,
                'savings_percentage': round(savings_percentage, 2)
            },
            
            # Bulk Pricing Tiers
            'bulk_pricing': {
                'tier_1': {
                    'quantity': input_data['bulk_tier_1_quantity'],
                    'price': input_data['bulk_tier_1_price']
                } if input_data['bulk_tier_1_quantity'] else None,
                'tier_2': {
                    'quantity': input_data['bulk_tier_2_quantity'],
                    'price': input_data['bulk_tier_2_price']
                } if input_data['bulk_tier_2_quantity'] else None,
                'tier_3': {
                    'quantity': input_data['bulk_tier_3_quantity'],
                    'price': input_data['bulk_tier_3_price']
                } if input_data['bulk_tier_3_quantity'] else None
            },
            
            # Logistics Options
            'logistics_options': {
                'supplier_delivery': {
                    'available': bool(input_data['supplier_delivery_available']),
                    'fee': input_data['supplier_delivery_fee'],
                    'radius_km': input_data['supplier_delivery_radius_km'],
                    'minimum_order': input_data['supplier_delivery_minimum_order'],
                    'delivery_days': input_data['supplier_delivery_days']
                } if input_data['supplier_delivery_available'] else None,
                'platform_logistics': {
                    'available': bool(input_data['platform_logistics_available']),
                    'base_fee': input_data['platform_logistics_base_fee'],
                    'per_km_rate': input_data['platform_logistics_per_km_rate'],
                    'minimum_order': input_data['platform_logistics_minimum_order'],
                    'delivery_days': input_data['platform_logistics_days']
                } if input_data['platform_logistics_available'] else None,
                'farmer_pickup': {
                    'available': bool(input_data['farmer_pickup_available']),
                    'location': input_data['pickup_location_address'],
                    'discount_percentage': input_data['pickup_discount_percentage']
                } if input_data['farmer_pickup_available'] else None
            },
            
            # Available Logistics Providers
            'logistics_providers': logistics_formatted,
            
            # Product Information
            'product_info': {
                'supplier_name': input_data['supplier_name'],
                'application_rate': input_data['application_rate'],
                'application_method': input_data['application_method'],
                'crop_suitability': json.loads(input_data['crop_suitability']) if input_data['crop_suitability'] else [],
                'current_stock': input_data['current_stock']
            }
        }
        
        conn.close()
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dynamic_pricing_bp.route('/api/pricing/calculate-order', methods=['POST'])
def calculate_order_total():
    """
    Calculate total order cost with dynamic pricing and logistics
    
    Expected JSON payload:
    {
        "items": [
            {"input_id": 1, "quantity": 10},
            {"input_id": 2, "quantity": 5}
        ],
        "delivery_option": "platform_logistics",
        "logistics_provider_id": 1,
        "farmer_location": {"lat": 14.1694, "lon": 121.2441},
        "delivery_address": "Barangay San Jose, Laguna",
        "card_member": true,
        "express_delivery": false
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'items' not in data:
            return jsonify({'error': 'Items are required'}), 400
        
        conn = get_db_connection()
        
        # Initialize totals
        subtotal_wholesale = 0.0
        subtotal_retail = 0.0
        platform_margin_total = 0.0
        total_quantity = 0
        items_breakdown = []
        
        # Calculate item costs
        for item in data['items']:
            input_id = item['input_id']
            quantity = item['quantity']
            
            # Get input data
            input_data = conn.execute('''
                SELECT * FROM agricultural_inputs WHERE id = ? AND is_active = 1
            ''', (input_id,)).fetchone()
            
            if not input_data:
                return jsonify({'error': f'Input {input_id} not found'}), 404
            
            # Calculate bulk pricing
            unit_price = get_bulk_price(dict(input_data), quantity)
            wholesale_unit_price = input_data['wholesale_price']
            
            # Calculate totals for this item
            item_wholesale_total = wholesale_unit_price * quantity
            item_retail_total = unit_price * quantity
            item_margin = item_retail_total - item_wholesale_total
            
            # Add to overall totals
            subtotal_wholesale += item_wholesale_total
            subtotal_retail += item_retail_total
            platform_margin_total += item_margin
            total_quantity += quantity
            
            # Calculate savings vs market price
            market_price = input_data['market_retail_price'] or input_data['retail_price']
            market_total = market_price * quantity
            item_savings = market_total - item_retail_total
            
            items_breakdown.append({
                'input_id': input_id,
                'name': input_data['name'],
                'quantity': quantity,
                'unit_price': unit_price,
                'wholesale_unit_price': wholesale_unit_price,
                'retail_total': item_retail_total,
                'wholesale_total': item_wholesale_total,
                'platform_margin': item_margin,
                'market_price_per_unit': market_price,
                'market_total': market_total,
                'farmer_savings': item_savings,
                'bulk_discount_applied': unit_price < input_data['retail_price']
            })
        
        # Calculate delivery costs
        delivery_fee = 0.0
        logistics_provider_fee = 0.0
        platform_logistics_margin = 0.0
        delivery_info = {}
        
        delivery_option = data.get('delivery_option', 'farmer_pickup')
        
        if delivery_option == 'platform_logistics':
            logistics_provider_id = data.get('logistics_provider_id')
            if logistics_provider_id:
                logistics_data = conn.execute('''
                    SELECT * FROM logistics_options WHERE id = ? AND is_active = 1
                ''', (logistics_provider_id,)).fetchone()
                
                if logistics_data:
                    base_fee = logistics_data['base_delivery_fee']
                    per_km_rate = logistics_data['per_km_rate']
                    free_threshold = logistics_data['free_delivery_threshold']
                    express_surcharge = logistics_data['express_delivery_surcharge'] if data.get('express_delivery') else 0
                    
                    # Calculate distance-based fee (simplified - in real implementation, use actual coordinates)
                    estimated_distance = 15.0  # Default 15km
                    if data.get('farmer_location'):
                        # In real implementation, calculate actual distance
                        estimated_distance = 15.0
                    
                    # Calculate delivery fee
                    if subtotal_retail >= free_threshold:
                        delivery_fee = 0.0
                    else:
                        delivery_fee = base_fee + (per_km_rate * estimated_distance) + express_surcharge
                    
                    # Platform takes 20% margin on logistics
                    logistics_provider_fee = delivery_fee * 0.8
                    platform_logistics_margin = delivery_fee * 0.2
                    
                    delivery_info = {
                        'provider': logistics_data['provider_name'],
                        'base_fee': base_fee,
                        'distance_km': estimated_distance,
                        'distance_fee': per_km_rate * estimated_distance,
                        'express_surcharge': express_surcharge,
                        'free_delivery_threshold': free_threshold,
                        'delivery_days': logistics_data['express_delivery_days'] if data.get('express_delivery') else logistics_data['standard_delivery_days']
                    }
        
        elif delivery_option == 'supplier_delivery':
            # Use average supplier delivery fee (simplified)
            delivery_fee = 75.0  # Average supplier delivery fee
            logistics_provider_fee = delivery_fee
            platform_logistics_margin = 0.0
            
            delivery_info = {
                'provider': 'Supplier Direct',
                'delivery_fee': delivery_fee,
                'delivery_days': 1
            }
        
        elif delivery_option == 'farmer_pickup':
            delivery_fee = 0.0
            # Apply pickup discount
            pickup_discount = subtotal_retail * 0.02  # 2% pickup discount
            subtotal_retail -= pickup_discount
            
            delivery_info = {
                'provider': 'Farmer Pickup',
                'pickup_location': 'CARD MRI Center, Laguna',
                'pickup_discount': pickup_discount
            }
        
        # Apply CARD member discount
        card_member_discount = 0.0
        if data.get('card_member'):
            card_member_discount = subtotal_retail * 0.03  # 3% CARD member discount
        
        # Calculate final totals
        total_before_discount = subtotal_retail + delivery_fee
        total_discounts = card_member_discount
        final_total = total_before_discount - total_discounts
        
        # Total platform revenue
        total_platform_revenue = platform_margin_total + platform_logistics_margin
        
        response = {
            'order_summary': {
                'total_items': len(data['items']),
                'total_quantity': total_quantity,
                'subtotal_wholesale': round(subtotal_wholesale, 2),
                'subtotal_retail': round(subtotal_retail, 2),
                'platform_margin_total': round(platform_margin_total, 2),
                'delivery_fee': round(delivery_fee, 2),
                'card_member_discount': round(card_member_discount, 2),
                'total_amount': round(final_total, 2),
                'total_platform_revenue': round(total_platform_revenue, 2)
            },
            
            'pricing_breakdown': {
                'items': items_breakdown,
                'delivery': delivery_info,
                'discounts': {
                    'card_member_discount': round(card_member_discount, 2),
                    'pickup_discount': delivery_info.get('pickup_discount', 0.0)
                }
            },
            
            'farmer_benefits': {
                'total_market_price': sum(item['market_total'] for item in items_breakdown),
                'total_farmer_savings': sum(item['farmer_savings'] for item in items_breakdown) + card_member_discount,
                'savings_percentage': round((sum(item['farmer_savings'] for item in items_breakdown) + card_member_discount) / sum(item['market_total'] for item in items_breakdown) * 100, 2)
            },
            
            'delivery_option': delivery_option,
            'card_member': data.get('card_member', False),
            'express_delivery': data.get('express_delivery', False)
        }
        
        conn.close()
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dynamic_pricing_bp.route('/api/logistics/options', methods=['GET'])
def get_logistics_options():
    """
    Get all available logistics options
    
    Query parameters:
    - location: Filter by service area
    - min_order: Minimum order value
    """
    try:
        conn = get_db_connection()
        
        # Get query parameters
        location = request.args.get('location')
        min_order = request.args.get('min_order', type=float)
        
        # Base query
        query = 'SELECT * FROM logistics_options WHERE is_active = 1'
        params = []
        
        # Add filters
        if min_order:
            query += ' AND minimum_order_value <= ?'
            params.append(min_order)
        
        logistics_options = conn.execute(query, params).fetchall()
        
        options_formatted = []
        for option in logistics_options:
            # Parse service regions
            service_regions = json.loads(option['service_regions']) if option['service_regions'] else []
            operating_days = json.loads(option['operating_days']) if option['operating_days'] else []
            
            # Filter by location if specified
            if location and location not in service_regions:
                continue
            
            options_formatted.append({
                'id': option['id'],
                'provider_name': option['provider_name'],
                'provider_type': option['provider_type'],
                'service_regions': service_regions,
                'service_radius_km': option['service_radius_km'],
                'pricing': {
                    'base_delivery_fee': option['base_delivery_fee'],
                    'per_km_rate': option['per_km_rate'],
                    'minimum_order_value': option['minimum_order_value'],
                    'free_delivery_threshold': option['free_delivery_threshold']
                },
                'service_levels': {
                    'standard_delivery_days': option['standard_delivery_days'],
                    'express_delivery_days': option['express_delivery_days'],
                    'express_delivery_surcharge': option['express_delivery_surcharge']
                },
                'schedule': {
                    'operating_days': operating_days,
                    'operating_hours': option['operating_hours']
                }
            })
        
        conn.close()
        return jsonify({
            'logistics_options': options_formatted,
            'total_options': len(options_formatted)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dynamic_pricing_bp.route('/api/pricing/market-comparison', methods=['GET'])
def get_market_comparison():
    """
    Get market price comparison for all inputs
    """
    try:
        conn = get_db_connection()
        
        inputs = conn.execute('''
            SELECT id, name, category, brand, wholesale_price, retail_price, market_retail_price, platform_margin, margin_percentage
            FROM agricultural_inputs 
            WHERE is_active = 1
            ORDER BY category, name
        ''').fetchall()
        
        comparison_data = []
        for input_data in inputs:
            market_price = input_data['market_retail_price'] or input_data['retail_price']
            farmer_savings = market_price - input_data['retail_price']
            savings_percentage = (farmer_savings / market_price) * 100 if market_price > 0 else 0
            
            comparison_data.append({
                'input_id': input_data['id'],
                'name': input_data['name'],
                'category': input_data['category'],
                'brand': input_data['brand'],
                'platform_price': input_data['retail_price'],
                'market_price': market_price,
                'farmer_savings': farmer_savings,
                'savings_percentage': round(savings_percentage, 2),
                'platform_margin': input_data['platform_margin'],
                'margin_percentage': input_data['margin_percentage']
            })
        
        # Calculate summary statistics
        total_inputs = len(comparison_data)
        avg_savings_percentage = sum(item['savings_percentage'] for item in comparison_data) / total_inputs if total_inputs > 0 else 0
        avg_margin_percentage = sum(item['margin_percentage'] for item in comparison_data) / total_inputs if total_inputs > 0 else 0
        
        conn.close()
        return jsonify({
            'market_comparison': comparison_data,
            'summary': {
                'total_inputs': total_inputs,
                'average_farmer_savings_percentage': round(avg_savings_percentage, 2),
                'average_platform_margin_percentage': round(avg_margin_percentage, 2)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dynamic_pricing_bp.route('/api/pricing/analytics', methods=['GET'])
def get_pricing_analytics():
    """
    Get pricing analytics and trends
    
    Query parameters:
    - period: daily, weekly, monthly
    - category: Filter by input category
    """
    try:
        conn = get_db_connection()
        
        period = request.args.get('period', 'daily')
        category = request.args.get('category')
        
        # Base query
        query = '''
            SELECT pa.*, ai.name, ai.brand
            FROM pricing_analytics pa
            LEFT JOIN agricultural_inputs ai ON pa.input_id = ai.id
            WHERE pa.period_type = ?
        '''
        params = [period]
        
        if category:
            query += ' AND pa.category = ?'
            params.append(category)
        
        query += ' ORDER BY pa.analysis_date DESC, pa.category, ai.name'
        
        analytics_data = conn.execute(query, params).fetchall()
        
        analytics_formatted = []
        for data in analytics_data:
            delivery_breakdown = json.loads(data['delivery_type_breakdown']) if data['delivery_type_breakdown'] else {}
            
            analytics_formatted.append({
                'analysis_date': data['analysis_date'],
                'input_id': data['input_id'],
                'input_name': data['name'],
                'brand': data['brand'],
                'category': data['category'],
                'pricing_metrics': {
                    'avg_wholesale_price': data['avg_wholesale_price'],
                    'avg_retail_price': data['avg_retail_price'],
                    'avg_platform_margin': data['avg_platform_margin'],
                    'avg_margin_percentage': data['avg_margin_percentage']
                },
                'volume_metrics': {
                    'total_quantity_sold': data['total_quantity_sold'],
                    'total_transactions': data['total_transactions'],
                    'total_revenue': data['total_revenue'],
                    'total_platform_revenue': data['total_platform_revenue']
                },
                'market_comparison': {
                    'market_price_comparison': data['market_price_comparison'],
                    'avg_delivery_fee': data['avg_delivery_fee']
                },
                'delivery_breakdown': delivery_breakdown
            })
        
        conn.close()
        return jsonify({
            'analytics': analytics_formatted,
            'period': period,
            'total_records': len(analytics_formatted)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dynamic_pricing_bp.route('/api/pricing/history/<int:input_id>', methods=['GET'])
def get_pricing_history(input_id):
    """
    Get pricing history for a specific input
    """
    try:
        conn = get_db_connection()
        
        # Get input information
        input_data = conn.execute('''
            SELECT name, category, brand FROM agricultural_inputs WHERE id = ?
        ''', (input_id,)).fetchone()
        
        if not input_data:
            return jsonify({'error': 'Input not found'}), 404
        
        # Get pricing history
        history = conn.execute('''
            SELECT * FROM input_pricing_history 
            WHERE input_id = ? 
            ORDER BY effective_from DESC
        ''', (input_id,)).fetchall()
        
        history_formatted = []
        for record in history:
            history_formatted.append({
                'effective_from': record['effective_from'],
                'effective_to': record['effective_to'],
                'wholesale_price': record['wholesale_price'],
                'retail_price': record['retail_price'],
                'platform_margin': record['platform_margin'],
                'margin_percentage': record['margin_percentage'],
                'change_reason': record['change_reason']
            })
        
        conn.close()
        return jsonify({
            'input_info': {
                'input_id': input_id,
                'name': input_data['name'],
                'category': input_data['category'],
                'brand': input_data['brand']
            },
            'pricing_history': history_formatted,
            'total_records': len(history_formatted)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@dynamic_pricing_bp.route('/api/pricing/health', methods=['GET'])
def pricing_health_check():
    """Health check for pricing API"""
    try:
        conn = get_db_connection()
        
        # Check database connectivity
        input_count = conn.execute('SELECT COUNT(*) FROM agricultural_inputs WHERE is_active = 1').fetchone()[0]
        logistics_count = conn.execute('SELECT COUNT(*) FROM logistics_options WHERE is_active = 1').fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'active_inputs': input_count,
            'active_logistics_options': logistics_count,
            'features': [
                'dynamic_pricing',
                'bulk_discounts',
                'logistics_options',
                'market_comparison',
                'pricing_analytics',
                'card_member_benefits'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
