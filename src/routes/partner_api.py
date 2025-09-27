"""
Partner API routes for external integrations
"""

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, or_, func

from src.models.user import db, User, Organization, AuditLog
from src.models.partner_api import (
    PartnerAPIKey, APIUsageLog, PartnerIntegration, WebhookEvent,
    PartnerType, APIKeyStatus
)
from src.middleware.partner_api import (
    require_partner_api_key, validate_partner_request_data, 
    PartnerAPIResponse, add_cors_headers
)
from src.routes.auth import log_audit_event

partner_api_bp = Blueprint('partner_api', __name__)

# Add CORS support for all partner API routes
@partner_api_bp.after_request
def after_request(response):
    return add_cors_headers(response)

@partner_api_bp.route('/partners/health', methods=['GET'])
def partner_api_health():
    """Health check endpoint for partner APIs"""
    return PartnerAPIResponse.success(
        data={'status': 'healthy', 'version': '1.0.0'},
        message='Partner API is operational'
    )

@partner_api_bp.route('/partners/auth/verify', methods=['GET'])
@require_partner_api_key()
def verify_api_key():
    """Verify API key and return key information"""
    api_key = g.partner_api_key
    organization = g.partner_organization
    
    return PartnerAPIResponse.success(
        data={
            'api_key_info': {
                'key_name': api_key.key_name,
                'partner_type': api_key.partner_type.value,
                'organization': {
                    'id': organization.id,
                    'name': organization.name,
                    'type': organization.type
                },
                'rate_limits': {
                    'per_minute': api_key.rate_limit_per_minute,
                    'per_hour': api_key.rate_limit_per_hour,
                    'per_day': api_key.rate_limit_per_day
                },
                'created_at': api_key.created_at.isoformat(),
                'last_used_at': api_key.last_used_at.isoformat() if api_key.last_used_at else None
            }
        },
        message='API key is valid'
    )

# Input Supplier API Endpoints
@partner_api_bp.route('/partners/input-suppliers/products', methods=['GET'])
@require_partner_api_key(allowed_partner_types=[PartnerType.INPUT_SUPPLIER])
def get_input_supplier_products():
    """Get products for input supplier"""
    organization = g.partner_organization
    
    # In a real implementation, this would fetch from a products table
    # For demo purposes, return mock data
    products = [
        {
            'id': 1,
            'name': 'NPK Fertilizer 14-14-14',
            'category': 'fertilizer',
            'price': 1250.00,
            'unit': 'kg',
            'stock_quantity': 500,
            'description': 'Balanced NPK fertilizer for general crop nutrition'
        },
        {
            'id': 2,
            'name': 'Urea 46-0-0',
            'category': 'fertilizer',
            'price': 1100.00,
            'unit': 'kg',
            'stock_quantity': 750,
            'description': 'High nitrogen fertilizer for vegetative growth'
        }
    ]
    
    log_audit_event(
        action='PARTNER_API_PRODUCTS_ACCESSED',
        resource='partner_api',
        details={'partner_type': 'input_supplier', 'organization_id': organization.id},
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'products': products},
        message='Products retrieved successfully'
    )

@partner_api_bp.route('/partners/input-suppliers/orders', methods=['POST'])
@require_partner_api_key(allowed_partner_types=[PartnerType.INPUT_SUPPLIER])
@validate_partner_request_data(required_fields=['farmer_id', 'products', 'delivery_address'])
def create_input_order():
    """Create a new input order"""
    organization = g.partner_organization
    data = g.validated_data
    
    # Validate farmer exists
    farmer_id = data['farmer_id']
    farmer = User.query.get(farmer_id)
    if not farmer:
        return PartnerAPIResponse.error('Farmer not found', code='FARMER_NOT_FOUND', status_code=404)
    
    # Calculate order total
    total_amount = 0
    for product in data['products']:
        total_amount += product.get('quantity', 0) * product.get('unit_price', 0)
    
    # Create order (in real implementation, this would be saved to database)
    order = {
        'id': f"ORD-{datetime.now().strftime('%Y%m%d')}-{farmer_id}",
        'farmer_id': farmer_id,
        'supplier_organization_id': organization.id,
        'products': data['products'],
        'delivery_address': data['delivery_address'],
        'total_amount': total_amount,
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'estimated_delivery': (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    }
    
    log_audit_event(
        action='PARTNER_ORDER_CREATED',
        resource='order',
        resource_id=order['id'],
        details={
            'farmer_id': farmer_id,
            'total_amount': total_amount,
            'supplier_organization_id': organization.id
        },
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'order': order},
        message='Order created successfully'
    )

# Logistics Partner API Endpoints
@partner_api_bp.route('/partners/logistics/shipments', methods=['GET'])
@require_partner_api_key(allowed_partner_types=[PartnerType.LOGISTICS_PARTNER])
def get_logistics_shipments():
    """Get shipments for logistics partner"""
    organization = g.partner_organization
    
    # Query parameters
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Mock shipments data
    all_shipments = [
        {
            'id': f'SHIP-{i:04d}',
            'order_id': f'ORD-20241201-{i}',
            'pickup_address': f'Warehouse {i % 3 + 1}, Metro Manila',
            'delivery_address': f'Farm {i}, Region {i % 4 + 1}',
            'status': ['pending', 'in_transit', 'delivered'][i % 3],
            'created_at': (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            'estimated_delivery': (datetime.now(timezone.utc) + timedelta(days=2-i%3)).isoformat()
        }
        for i in range(1, 51)  # 50 mock shipments
    ]
    
    # Filter by status if provided
    if status:
        shipments = [s for s in all_shipments if s['status'] == status]
    else:
        shipments = all_shipments
    
    # Pagination
    total = len(shipments)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_shipments = shipments[start:end]
    
    log_audit_event(
        action='PARTNER_API_SHIPMENTS_ACCESSED',
        resource='partner_api',
        details={'partner_type': 'logistics', 'organization_id': organization.id, 'status_filter': status},
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.paginated(
        data=paginated_shipments,
        page=page,
        per_page=per_page,
        total=total,
        endpoint='/api/partners/logistics/shipments'
    )

@partner_api_bp.route('/partners/logistics/shipments/<shipment_id>/status', methods=['PUT'])
@require_partner_api_key(allowed_partner_types=[PartnerType.LOGISTICS_PARTNER])
@validate_partner_request_data(required_fields=['status'])
def update_shipment_status(shipment_id):
    """Update shipment status"""
    organization = g.partner_organization
    data = g.validated_data
    
    new_status = data['status']
    valid_statuses = ['pending', 'picked_up', 'in_transit', 'delivered', 'cancelled']
    
    if new_status not in valid_statuses:
        return PartnerAPIResponse.error(
            f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
            code='INVALID_STATUS'
        )
    
    # Update shipment (in real implementation, this would update database)
    updated_shipment = {
        'id': shipment_id,
        'status': new_status,
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'updated_by': organization.name
    }
    
    log_audit_event(
        action='PARTNER_SHIPMENT_STATUS_UPDATED',
        resource='shipment',
        resource_id=shipment_id,
        details={'new_status': new_status, 'logistics_partner_id': organization.id},
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'shipment': updated_shipment},
        message='Shipment status updated successfully'
    )

# Financial Partner API Endpoints
@partner_api_bp.route('/partners/financial/credit-check', methods=['POST'])
@require_partner_api_key(allowed_partner_types=[PartnerType.FINANCIAL_PARTNER])
@validate_partner_request_data(required_fields=['farmer_id', 'requested_amount'])
def perform_credit_check():
    """Perform credit check for farmer"""
    organization = g.partner_organization
    data = g.validated_data
    
    farmer_id = data['farmer_id']
    requested_amount = data['requested_amount']
    
    # Validate farmer exists
    farmer = User.query.get(farmer_id)
    if not farmer:
        return PartnerAPIResponse.error('Farmer not found', code='FARMER_NOT_FOUND', status_code=404)
    
    # Mock credit check logic
    credit_score = min(850, max(300, 650 + (farmer_id % 200)))  # Mock score between 300-850
    approved_amount = min(requested_amount, credit_score * 100)  # Simple calculation
    
    credit_result = {
        'farmer_id': farmer_id,
        'requested_amount': requested_amount,
        'credit_score': credit_score,
        'approved_amount': approved_amount,
        'approval_status': 'approved' if approved_amount >= requested_amount * 0.8 else 'partial',
        'interest_rate': 12.5,  # Annual percentage rate
        'term_months': 12,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    }
    
    log_audit_event(
        action='PARTNER_CREDIT_CHECK_PERFORMED',
        resource='credit_check',
        details={
            'farmer_id': farmer_id,
            'requested_amount': requested_amount,
            'approved_amount': approved_amount,
            'financial_partner_id': organization.id
        },
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'credit_check': credit_result},
        message='Credit check completed successfully'
    )

@partner_api_bp.route('/partners/financial/loans', methods=['POST'])
@require_partner_api_key(allowed_partner_types=[PartnerType.FINANCIAL_PARTNER])
@validate_partner_request_data(required_fields=['farmer_id', 'amount', 'purpose'])
def create_loan():
    """Create a new loan for farmer"""
    organization = g.partner_organization
    data = g.validated_data
    
    farmer_id = data['farmer_id']
    amount = data['amount']
    purpose = data['purpose']
    
    # Validate farmer exists
    farmer = User.query.get(farmer_id)
    if not farmer:
        return PartnerAPIResponse.error('Farmer not found', code='FARMER_NOT_FOUND', status_code=404)
    
    # Create loan record
    loan = {
        'id': f"LOAN-{datetime.now().strftime('%Y%m%d')}-{farmer_id}",
        'farmer_id': farmer_id,
        'lender_organization_id': organization.id,
        'amount': amount,
        'purpose': purpose,
        'interest_rate': 12.5,
        'term_months': 12,
        'status': 'approved',
        'disbursement_date': datetime.now(timezone.utc).isoformat(),
        'maturity_date': (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    log_audit_event(
        action='PARTNER_LOAN_CREATED',
        resource='loan',
        resource_id=loan['id'],
        details={
            'farmer_id': farmer_id,
            'amount': amount,
            'purpose': purpose,
            'lender_organization_id': organization.id
        },
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'loan': loan},
        message='Loan created successfully'
    )

# Buyer/Processor API Endpoints
@partner_api_bp.route('/partners/buyers/produce-listings', methods=['GET'])
@require_partner_api_key(allowed_partner_types=[PartnerType.BUYER_PROCESSOR])
def get_produce_listings():
    """Get available produce listings"""
    organization = g.partner_organization
    
    # Query parameters
    crop_type = request.args.get('crop_type')
    region = request.args.get('region')
    min_quantity = request.args.get('min_quantity', type=float)
    
    # Mock produce listings
    listings = [
        {
            'id': f'PROD-{i:04d}',
            'farmer_id': i,
            'crop_type': ['rice', 'corn', 'vegetables'][i % 3],
            'variety': ['IR64', 'Yellow Corn', 'Tomatoes'][i % 3],
            'quantity': (i % 10 + 1) * 100,  # 100-1000 kg
            'unit': 'kg',
            'price_per_unit': [25.50, 18.75, 45.00][i % 3],
            'harvest_date': (datetime.now(timezone.utc) + timedelta(days=i % 30)).isoformat(),
            'location': f'Region {i % 4 + 1}',
            'quality_grade': ['A', 'B', 'A'][i % 3],
            'organic_certified': i % 4 == 0,
            'available_until': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        for i in range(1, 26)  # 25 mock listings
    ]
    
    # Apply filters
    filtered_listings = listings
    
    if crop_type:
        filtered_listings = [l for l in filtered_listings if l['crop_type'] == crop_type]
    
    if region:
        filtered_listings = [l for l in filtered_listings if l['location'] == region]
    
    if min_quantity:
        filtered_listings = [l for l in filtered_listings if l['quantity'] >= min_quantity]
    
    log_audit_event(
        action='PARTNER_API_PRODUCE_LISTINGS_ACCESSED',
        resource='partner_api',
        details={
            'partner_type': 'buyer_processor',
            'organization_id': organization.id,
            'filters': {'crop_type': crop_type, 'region': region, 'min_quantity': min_quantity}
        },
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'listings': filtered_listings},
        message='Produce listings retrieved successfully'
    )

@partner_api_bp.route('/partners/buyers/purchase-orders', methods=['POST'])
@require_partner_api_key(allowed_partner_types=[PartnerType.BUYER_PROCESSOR])
@validate_partner_request_data(required_fields=['listing_id', 'quantity', 'offered_price'])
def create_purchase_order():
    """Create a purchase order for produce"""
    organization = g.partner_organization
    data = g.validated_data
    
    listing_id = data['listing_id']
    quantity = data['quantity']
    offered_price = data['offered_price']
    
    # Create purchase order
    purchase_order = {
        'id': f"PO-{datetime.now().strftime('%Y%m%d')}-{listing_id}",
        'listing_id': listing_id,
        'buyer_organization_id': organization.id,
        'quantity': quantity,
        'offered_price_per_unit': offered_price,
        'total_amount': quantity * offered_price,
        'status': 'pending',
        'delivery_terms': data.get('delivery_terms', 'FOB Farm'),
        'payment_terms': data.get('payment_terms', 'Net 30'),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }
    
    log_audit_event(
        action='PARTNER_PURCHASE_ORDER_CREATED',
        resource='purchase_order',
        resource_id=purchase_order['id'],
        details={
            'listing_id': listing_id,
            'quantity': quantity,
            'total_amount': purchase_order['total_amount'],
            'buyer_organization_id': organization.id
        },
        organization_id=organization.id
    )
    
    return PartnerAPIResponse.success(
        data={'purchase_order': purchase_order},
        message='Purchase order created successfully'
    )

# API Usage Analytics for Partners
@partner_api_bp.route('/partners/analytics/usage', methods=['GET'])
@require_partner_api_key()
def get_api_usage_analytics():
    """Get API usage analytics for the partner"""
    api_key = g.partner_api_key
    organization = g.partner_organization
    
    # Query parameters
    days = request.args.get('days', 30, type=int)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get usage statistics
    total_requests = APIUsageLog.query.filter(
        APIUsageLog.api_key_id == api_key.id,
        APIUsageLog.timestamp >= start_date
    ).count()
    
    successful_requests = APIUsageLog.query.filter(
        APIUsageLog.api_key_id == api_key.id,
        APIUsageLog.timestamp >= start_date,
        APIUsageLog.status_code < 400
    ).count()
    
    # Get endpoint usage breakdown
    endpoint_usage = db.session.query(
        APIUsageLog.endpoint,
        func.count(APIUsageLog.id).label('count')
    ).filter(
        APIUsageLog.api_key_id == api_key.id,
        APIUsageLog.timestamp >= start_date
    ).group_by(APIUsageLog.endpoint).all()
    
    # Get daily usage trend
    daily_usage = []
    for i in range(days):
        day_start = (end_date - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        daily_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.timestamp >= day_start,
            APIUsageLog.timestamp < day_end
        ).count()
        
        daily_usage.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'requests': daily_count
        })
    
    daily_usage.reverse()  # Show oldest to newest
    
    analytics = {
        'period': {
            'days': days,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'summary': {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'average_requests_per_day': total_requests / days if days > 0 else 0
        },
        'endpoint_usage': [
            {'endpoint': endpoint, 'requests': count}
            for endpoint, count in endpoint_usage
        ],
        'daily_usage': daily_usage,
        'rate_limits': {
            'per_minute': api_key.rate_limit_per_minute,
            'per_hour': api_key.rate_limit_per_hour,
            'per_day': api_key.rate_limit_per_day
        }
    }
    
    return PartnerAPIResponse.success(
        data={'analytics': analytics},
        message='API usage analytics retrieved successfully'
    )
