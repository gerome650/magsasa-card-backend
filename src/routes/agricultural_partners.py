from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import uuid
from ..models.user import db, User, Organization
from ..models.agricultural import (
    Farmer, Farm, Crop, AgriculturalInput, FarmActivity,
    AgriculturalOrganization
)
from ..models.partner_api import PartnerAPIKey, PartnerAPIUsage
from ..middleware.agricultural_auth import require_agricultural_permission
from ..middleware.partner_api import partner_api_required
import json

agricultural_partners_bp = Blueprint('agricultural_partners', __name__)

# ============================================================================
# INPUT SUPPLIER PARTNER APIs
# ============================================================================

@agricultural_partners_bp.route('/api/partners/input-suppliers/products', methods=['GET'])
@partner_api_required(['input_supplier'])
def get_input_products():
    """Get available agricultural input products for suppliers"""
    try:
        # Get partner organization from API key
        partner_org_id = request.partner_org_id
        
        # Get all agricultural inputs available for this supplier
        inputs = AgriculturalInput.query.filter_by(
            supplier_organization_id=partner_org_id
        ).all()
        
        products = []
        for input_item in inputs:
            products.append({
                'id': input_item.id,
                'name': input_item.name,
                'category': input_item.category,
                'brand': input_item.brand,
                'active_ingredient': input_item.active_ingredient,
                'package_size': input_item.package_size,
                'unit': input_item.unit,
                'cost_price': float(input_item.cost_price),
                'selling_price': float(input_item.selling_price),
                'stock_quantity': input_item.stock_quantity,
                'reorder_level': input_item.reorder_level,
                'application_rate': input_item.application_rate,
                'suitable_crops': input_item.suitable_crops.split(',') if input_item.suitable_crops else [],
                'created_at': input_item.created_at.isoformat(),
                'updated_at': input_item.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'products': products,
            'total_count': len(products),
            'supplier_organization': partner_org_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting input products: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve products'}), 500

@agricultural_partners_bp.route('/api/partners/input-suppliers/orders', methods=['POST'])
@partner_api_required(['input_supplier'])
def create_input_order():
    """Create a new order for agricultural inputs"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['farmer_id', 'products', 'delivery_address', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Verify farmer exists
        farmer = Farmer.query.get(data['farmer_id'])
        if not farmer:
            return jsonify({'success': False, 'message': 'Farmer not found'}), 404
        
        # Create order record (simplified - would integrate with order management system)
        order_data = {
            'id': str(uuid.uuid4()),
            'farmer_id': data['farmer_id'],
            'supplier_organization_id': request.partner_org_id,
            'products': data['products'],
            'total_amount': data.get('total_amount', 0),
            'delivery_address': data['delivery_address'],
            'payment_method': data['payment_method'],
            'status': 'pending',
            'order_date': datetime.utcnow().isoformat(),
            'expected_delivery': (datetime.utcnow() + timedelta(days=3)).isoformat()
        }
        
        # In a real system, this would be saved to an Orders table
        # For now, we'll return the order confirmation
        
        return jsonify({
            'success': True,
            'message': 'Order created successfully',
            'order': order_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating input order: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to create order'}), 500

@agricultural_partners_bp.route('/api/partners/input-suppliers/inventory', methods=['PUT'])
@partner_api_required(['input_supplier'])
def update_inventory():
    """Update inventory levels for agricultural inputs"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'product_id' not in data or 'quantity_change' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Get the product
        product = AgriculturalInput.query.filter_by(
            id=data['product_id'],
            supplier_organization_id=request.partner_org_id
        ).first()
        
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        
        # Update inventory
        old_quantity = product.stock_quantity
        product.stock_quantity += data['quantity_change']
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory updated successfully',
            'product_id': product.id,
            'old_quantity': old_quantity,
            'new_quantity': product.stock_quantity,
            'change': data['quantity_change']
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating inventory: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update inventory'}), 500

# ============================================================================
# LOGISTICS PARTNER APIs
# ============================================================================

@agricultural_partners_bp.route('/api/partners/logistics/shipments', methods=['GET'])
@partner_api_required(['logistics_partner'])
def get_shipments():
    """Get shipments assigned to logistics partner"""
    try:
        # In a real system, this would query a Shipments table
        # For now, we'll return mock data
        
        shipments = [
            {
                'id': 'SHIP-001',
                'order_id': 'ORD-001',
                'farmer_name': 'Maria Santos',
                'pickup_address': 'Supplier Warehouse, Laguna',
                'delivery_address': 'Farm Address, Calauan, Laguna',
                'products': ['NPK Fertilizer 14-14-14', 'Rice Seeds'],
                'status': 'in_transit',
                'pickup_date': '2024-09-25',
                'expected_delivery': '2024-09-27',
                'driver_name': 'Juan Delivery',
                'vehicle_plate': 'ABC-1234'
            },
            {
                'id': 'SHIP-002',
                'order_id': 'ORD-002',
                'farmer_name': 'Pedro Garcia',
                'pickup_address': 'Supplier Warehouse, Laguna',
                'delivery_address': 'Farm Address, Bay, Laguna',
                'products': ['Pesticide', 'Corn Seeds'],
                'status': 'pending_pickup',
                'pickup_date': '2024-09-27',
                'expected_delivery': '2024-09-28',
                'driver_name': None,
                'vehicle_plate': None
            }
        ]
        
        return jsonify({
            'success': True,
            'shipments': shipments,
            'total_count': len(shipments)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting shipments: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve shipments'}), 500

@agricultural_partners_bp.route('/api/partners/logistics/shipments/<shipment_id>/status', methods=['PUT'])
@partner_api_required(['logistics_partner'])
def update_shipment_status(shipment_id):
    """Update shipment status and tracking information"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'status' not in data:
            return jsonify({'success': False, 'message': 'Missing status field'}), 400
        
        valid_statuses = ['pending_pickup', 'picked_up', 'in_transit', 'delivered', 'failed_delivery']
        if data['status'] not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        # In a real system, this would update the Shipments table
        # For now, we'll return a success response
        
        update_data = {
            'shipment_id': shipment_id,
            'old_status': 'in_transit',  # Mock old status
            'new_status': data['status'],
            'updated_at': datetime.utcnow().isoformat(),
            'notes': data.get('notes', ''),
            'location': data.get('location', ''),
            'driver_name': data.get('driver_name', ''),
            'vehicle_plate': data.get('vehicle_plate', '')
        }
        
        return jsonify({
            'success': True,
            'message': 'Shipment status updated successfully',
            'update': update_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating shipment status: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update shipment status'}), 500

# ============================================================================
# FINANCIAL PARTNER APIs
# ============================================================================

@agricultural_partners_bp.route('/api/partners/financial/credit-check', methods=['POST'])
@partner_api_required(['financial_partner'])
def perform_credit_check():
    """Perform credit assessment for farmer loan applications"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['farmer_id', 'loan_amount', 'loan_purpose']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Get farmer information
        farmer = Farmer.query.get(data['farmer_id'])
        if not farmer:
            return jsonify({'success': False, 'message': 'Farmer not found'}), 404
        
        # Perform credit assessment (simplified algorithm)
        loan_amount = float(data['loan_amount'])
        
        # Credit scoring factors
        credit_score = 0
        
        # Farm size factor (larger farms = higher score)
        if farmer.farms:
            total_farm_size = sum(farm.size_hectares for farm in farmer.farms)
            credit_score += min(total_farm_size * 10, 50)  # Max 50 points
        
        # Experience factor
        if farmer.years_farming:
            credit_score += min(farmer.years_farming * 2, 30)  # Max 30 points
        
        # CARD BDSFI membership bonus
        if farmer.card_bdsfi_member:
            credit_score += 20
        
        # Income factor (if available)
        if farmer.annual_income:
            income_ratio = loan_amount / farmer.annual_income
            if income_ratio <= 0.3:
                credit_score += 20
            elif income_ratio <= 0.5:
                credit_score += 10
        
        # Determine approval status
        if credit_score >= 70:
            approval_status = 'approved'
            interest_rate = 8.5
        elif credit_score >= 50:
            approval_status = 'conditional'
            interest_rate = 12.0
        else:
            approval_status = 'declined'
            interest_rate = None
        
        credit_assessment = {
            'farmer_id': data['farmer_id'],
            'farmer_name': farmer.name,
            'loan_amount': loan_amount,
            'loan_purpose': data['loan_purpose'],
            'credit_score': credit_score,
            'approval_status': approval_status,
            'interest_rate': interest_rate,
            'max_approved_amount': loan_amount if approval_status == 'approved' else loan_amount * 0.7,
            'assessment_date': datetime.utcnow().isoformat(),
            'valid_until': (datetime.utcnow() + timedelta(days=30)).isoformat(),
            'conditions': [] if approval_status == 'approved' else ['Collateral required', 'Co-signer needed'] if approval_status == 'conditional' else ['Insufficient credit history']
        }
        
        return jsonify({
            'success': True,
            'credit_assessment': credit_assessment
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error performing credit check: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to perform credit check'}), 500

@agricultural_partners_bp.route('/api/partners/financial/loans', methods=['POST'])
@partner_api_required(['financial_partner'])
def create_loan():
    """Create a new loan for approved farmers"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['farmer_id', 'loan_amount', 'interest_rate', 'term_months', 'purpose']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Get farmer information
        farmer = Farmer.query.get(data['farmer_id'])
        if not farmer:
            return jsonify({'success': False, 'message': 'Farmer not found'}), 404
        
        # Create loan record (simplified)
        loan_data = {
            'id': str(uuid.uuid4()),
            'farmer_id': data['farmer_id'],
            'farmer_name': farmer.name,
            'financial_partner_id': request.partner_org_id,
            'loan_amount': float(data['loan_amount']),
            'interest_rate': float(data['interest_rate']),
            'term_months': int(data['term_months']),
            'purpose': data['purpose'],
            'status': 'active',
            'disbursement_date': datetime.utcnow().isoformat(),
            'maturity_date': (datetime.utcnow() + timedelta(days=int(data['term_months']) * 30)).isoformat(),
            'monthly_payment': (float(data['loan_amount']) * (1 + float(data['interest_rate'])/100)) / int(data['term_months']),
            'outstanding_balance': float(data['loan_amount']),
            'collateral': data.get('collateral', ''),
            'guarantor': data.get('guarantor', '')
        }
        
        return jsonify({
            'success': True,
            'message': 'Loan created successfully',
            'loan': loan_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating loan: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to create loan'}), 500

# ============================================================================
# BUYER/PROCESSOR PARTNER APIs
# ============================================================================

@agricultural_partners_bp.route('/api/partners/buyers/produce-listings', methods=['GET'])
@partner_api_required(['buyer_processor'])
def get_produce_listings():
    """Get available produce listings for buyers"""
    try:
        # Get query parameters
        crop_type = request.args.get('crop_type')
        location = request.args.get('location')
        min_quantity = request.args.get('min_quantity', type=float)
        
        # In a real system, this would query harvest records
        # For now, we'll return mock data
        
        produce_listings = [
            {
                'id': 'PROD-001',
                'farmer_id': 1,
                'farmer_name': 'Maria Santos',
                'farm_location': 'Calauan, Laguna',
                'crop_type': 'Rice',
                'variety': 'IR64',
                'quantity_available': 2.5,
                'unit': 'metric_tons',
                'quality_grade': 'Premium',
                'harvest_date': '2024-09-20',
                'asking_price': 25000.0,
                'price_unit': 'per_metric_ton',
                'moisture_content': 14.0,
                'purity_percentage': 98.5,
                'storage_location': 'On-farm warehouse',
                'contact_phone': '+63 917 123 4567',
                'available_until': '2024-10-20'
            },
            {
                'id': 'PROD-002',
                'farmer_id': 2,
                'farmer_name': 'Pedro Garcia',
                'farm_location': 'Bay, Laguna',
                'crop_type': 'Corn',
                'variety': 'Yellow Corn',
                'quantity_available': 1.8,
                'unit': 'metric_tons',
                'quality_grade': 'Grade A',
                'harvest_date': '2024-09-22',
                'asking_price': 18000.0,
                'price_unit': 'per_metric_ton',
                'moisture_content': 15.5,
                'purity_percentage': 97.0,
                'storage_location': 'Cooperative warehouse',
                'contact_phone': '+63 917 234 5678',
                'available_until': '2024-11-15'
            }
        ]
        
        # Apply filters
        filtered_listings = produce_listings
        
        if crop_type:
            filtered_listings = [p for p in filtered_listings if p['crop_type'].lower() == crop_type.lower()]
        
        if location:
            filtered_listings = [p for p in filtered_listings if location.lower() in p['farm_location'].lower()]
        
        if min_quantity:
            filtered_listings = [p for p in filtered_listings if p['quantity_available'] >= min_quantity]
        
        return jsonify({
            'success': True,
            'produce_listings': filtered_listings,
            'total_count': len(filtered_listings),
            'filters_applied': {
                'crop_type': crop_type,
                'location': location,
                'min_quantity': min_quantity
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting produce listings: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve produce listings'}), 500

@agricultural_partners_bp.route('/api/partners/buyers/purchase-orders', methods=['POST'])
@partner_api_required(['buyer_processor'])
def create_purchase_order():
    """Create a purchase order for produce"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['produce_listing_id', 'quantity', 'offered_price', 'delivery_terms']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Create purchase order (simplified)
        purchase_order = {
            'id': str(uuid.uuid4()),
            'produce_listing_id': data['produce_listing_id'],
            'buyer_organization_id': request.partner_org_id,
            'quantity': float(data['quantity']),
            'offered_price': float(data['offered_price']),
            'total_amount': float(data['quantity']) * float(data['offered_price']),
            'delivery_terms': data['delivery_terms'],
            'payment_terms': data.get('payment_terms', 'Net 30'),
            'quality_requirements': data.get('quality_requirements', {}),
            'delivery_date': data.get('delivery_date'),
            'status': 'pending',
            'order_date': datetime.utcnow().isoformat(),
            'notes': data.get('notes', '')
        }
        
        return jsonify({
            'success': True,
            'message': 'Purchase order created successfully',
            'purchase_order': purchase_order
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating purchase order: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to create purchase order'}), 500

# ============================================================================
# SUPPLY CHAIN INTEGRATION APIs
# ============================================================================

@agricultural_partners_bp.route('/api/partners/supply-chain/track', methods=['GET'])
@partner_api_required(['input_supplier', 'logistics_partner', 'buyer_processor'])
def track_supply_chain():
    """Track items through the supply chain"""
    try:
        tracking_id = request.args.get('tracking_id')
        if not tracking_id:
            return jsonify({'success': False, 'message': 'Missing tracking_id parameter'}), 400
        
        # Mock supply chain tracking data
        tracking_data = {
            'tracking_id': tracking_id,
            'current_status': 'in_transit',
            'timeline': [
                {
                    'timestamp': '2024-09-25T08:00:00Z',
                    'status': 'order_placed',
                    'location': 'Input Supplier Warehouse',
                    'description': 'Order received and confirmed',
                    'handler': 'Input Supplier'
                },
                {
                    'timestamp': '2024-09-25T14:30:00Z',
                    'status': 'picked_up',
                    'location': 'Input Supplier Warehouse',
                    'description': 'Package picked up by logistics partner',
                    'handler': 'Logistics Partner'
                },
                {
                    'timestamp': '2024-09-26T09:15:00Z',
                    'status': 'in_transit',
                    'location': 'Highway, En route to Laguna',
                    'description': 'Package in transit to destination',
                    'handler': 'Logistics Partner'
                }
            ],
            'estimated_delivery': '2024-09-27T16:00:00Z',
            'recipient': {
                'name': 'Maria Santos',
                'location': 'Calauan, Laguna',
                'contact': '+63 917 123 4567'
            }
        }
        
        return jsonify({
            'success': True,
            'tracking': tracking_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error tracking supply chain: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to track item'}), 500

@agricultural_partners_bp.route('/api/partners/supply-chain/analytics', methods=['GET'])
@partner_api_required(['input_supplier', 'logistics_partner', 'financial_partner', 'buyer_processor'])
def get_supply_chain_analytics():
    """Get supply chain analytics for partners"""
    try:
        partner_type = request.partner_type
        
        # Mock analytics data based on partner type
        if partner_type == 'input_supplier':
            analytics = {
                'total_orders': 156,
                'total_revenue': 2340000.0,
                'top_products': [
                    {'name': 'NPK Fertilizer 14-14-14', 'orders': 45, 'revenue': 675000.0},
                    {'name': 'Rice Seeds IR64', 'orders': 38, 'revenue': 456000.0},
                    {'name': 'Pesticide Cypermethrin', 'orders': 32, 'revenue': 384000.0}
                ],
                'monthly_trends': [
                    {'month': 'July', 'orders': 42, 'revenue': 630000.0},
                    {'month': 'August', 'orders': 48, 'revenue': 720000.0},
                    {'month': 'September', 'orders': 66, 'revenue': 990000.0}
                ]
            }
        elif partner_type == 'logistics_partner':
            analytics = {
                'total_deliveries': 234,
                'on_time_percentage': 94.5,
                'total_distance': 12450.0,
                'average_delivery_time': 1.8,
                'monthly_performance': [
                    {'month': 'July', 'deliveries': 72, 'on_time': 95.8},
                    {'month': 'August', 'deliveries': 78, 'on_time': 93.6},
                    {'month': 'September', 'deliveries': 84, 'on_time': 94.0}
                ]
            }
        elif partner_type == 'financial_partner':
            analytics = {
                'total_loans': 89,
                'total_disbursed': 15670000.0,
                'default_rate': 2.3,
                'average_loan_size': 176067.0,
                'loan_performance': [
                    {'month': 'July', 'loans': 28, 'amount': 4920000.0},
                    {'month': 'August', 'loans': 31, 'amount': 5456000.0},
                    {'month': 'September', 'loans': 30, 'amount': 5294000.0}
                ]
            }
        elif partner_type == 'buyer_processor':
            analytics = {
                'total_purchases': 67,
                'total_volume': 234.5,
                'total_value': 5876000.0,
                'average_price': 25043.0,
                'crop_breakdown': [
                    {'crop': 'Rice', 'volume': 156.7, 'value': 3918000.0},
                    {'crop': 'Corn', 'volume': 45.2, 'value': 1356000.0},
                    {'crop': 'Vegetables', 'volume': 32.6, 'value': 602000.0}
                ]
            }
        else:
            analytics = {'message': 'Analytics not available for this partner type'}
        
        return jsonify({
            'success': True,
            'partner_type': partner_type,
            'analytics': analytics,
            'period': 'Last 3 months',
            'generated_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting supply chain analytics: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve analytics'}), 500

# ============================================================================
# WEBHOOK ENDPOINTS FOR REAL-TIME INTEGRATION
# ============================================================================

@agricultural_partners_bp.route('/api/partners/webhooks/order-status', methods=['POST'])
@partner_api_required(['input_supplier', 'logistics_partner'])
def webhook_order_status():
    """Webhook endpoint for order status updates"""
    try:
        data = request.get_json()
        
        # Validate webhook data
        required_fields = ['order_id', 'status', 'timestamp']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Process the webhook (in a real system, this would update databases and notify relevant parties)
        webhook_response = {
            'received': True,
            'order_id': data['order_id'],
            'status': data['status'],
            'processed_at': datetime.utcnow().isoformat(),
            'partner_organization': request.partner_org_id
        }
        
        # Log the webhook for audit purposes
        current_app.logger.info(f"Webhook received from partner {request.partner_org_id}: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Webhook processed successfully',
            'response': webhook_response
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to process webhook'}), 500

@agricultural_partners_bp.route('/api/partners/webhooks/payment-notification', methods=['POST'])
@partner_api_required(['financial_partner'])
def webhook_payment_notification():
    """Webhook endpoint for payment notifications"""
    try:
        data = request.get_json()
        
        # Validate webhook data
        required_fields = ['transaction_id', 'amount', 'status', 'farmer_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Process payment notification
        payment_data = {
            'transaction_id': data['transaction_id'],
            'farmer_id': data['farmer_id'],
            'amount': float(data['amount']),
            'status': data['status'],
            'payment_method': data.get('payment_method', 'bank_transfer'),
            'processed_at': datetime.utcnow().isoformat(),
            'financial_partner': request.partner_org_id
        }
        
        return jsonify({
            'success': True,
            'message': 'Payment notification processed successfully',
            'payment': payment_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing payment webhook: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to process payment notification'}), 500

# ============================================================================
# PARTNER INTEGRATION HEALTH CHECK
# ============================================================================

@agricultural_partners_bp.route('/api/partners/health', methods=['GET'])
@partner_api_required(['input_supplier', 'logistics_partner', 'financial_partner', 'buyer_processor'])
def partner_health_check():
    """Health check endpoint for partner integrations"""
    try:
        health_data = {
            'status': 'healthy',
            'partner_organization': request.partner_org_id,
            'partner_type': request.partner_type,
            'api_version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'endpoints_available': [
                '/api/partners/supply-chain/track',
                '/api/partners/supply-chain/analytics',
                '/api/partners/webhooks/order-status'
            ]
        }
        
        # Add partner-specific endpoints
        if request.partner_type == 'input_supplier':
            health_data['endpoints_available'].extend([
                '/api/partners/input-suppliers/products',
                '/api/partners/input-suppliers/orders',
                '/api/partners/input-suppliers/inventory'
            ])
        elif request.partner_type == 'logistics_partner':
            health_data['endpoints_available'].extend([
                '/api/partners/logistics/shipments',
                '/api/partners/logistics/shipments/{id}/status'
            ])
        elif request.partner_type == 'financial_partner':
            health_data['endpoints_available'].extend([
                '/api/partners/financial/credit-check',
                '/api/partners/financial/loans',
                '/api/partners/webhooks/payment-notification'
            ])
        elif request.partner_type == 'buyer_processor':
            health_data['endpoints_available'].extend([
                '/api/partners/buyers/produce-listings',
                '/api/partners/buyers/purchase-orders'
            ])
        
        return jsonify({
            'success': True,
            'health': health_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in partner health check: {str(e)}")
        return jsonify({'success': False, 'message': 'Health check failed'}), 500
