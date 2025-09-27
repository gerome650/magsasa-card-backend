"""
MAGSASA-CARD Enhanced Platform - Agricultural Routes
Comprehensive agricultural operations management API endpoints
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, date, timedelta
import json

from src.models.user import db, User, Organization, AuditLog
from src.models.agricultural import (
    AgriculturalOrganization, Farmer, Farm, Field, Crop, FarmActivity,
    AgriculturalInput, InputTransaction, HarvestRecord, FarmAnalytics,
    WeatherData, FarmType, CropStage, ActivityType, InputType, TransactionStatus
)
from src.middleware.tenant import get_current_organization
from src.middleware.agricultural_auth import (
    require_agricultural_permission, require_farmer_access, require_farm_access,
    require_activity_access, require_input_access, require_analytics_access,
    get_user_data_filter, apply_data_filter
)
from src.models.agricultural_permissions import AgriculturalPermission

agricultural_bp = Blueprint('agricultural', __name__, url_prefix='/api/agricultural')

# Utility functions
def log_audit(action, resource, resource_id=None, details=None):
    """Log agricultural operations to audit trail"""
    try:
        current_user_id = get_jwt_identity()
        current_org = get_current_organization()
        
        audit_log = AuditLog(
            user_id=current_user_id,
            organization_id=current_org.id if current_org else None,
            action=action,
            resource=resource,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Audit logging failed: {str(e)}")

def require_role(allowed_roles):
    """Decorator to check if user has required role"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get('role')
            if user_role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Farmer Management Routes
@agricultural_bp.route('/farmers', methods=['GET'])
@jwt_required()
@require_farmer_access('view')
def get_farmers():
    """Get list of farmers with filtering and pagination"""
    try:
        current_org = get_current_organization()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query with organization filter
        query = Farmer.query
        if current_org:
            query = query.filter(Farmer.agricultural_org_id == current_org.id)
        
        # Apply filters
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(or_(
                Farmer.first_name.ilike(search_term),
                Farmer.last_name.ilike(search_term),
                Farmer.rsbsa_id.ilike(search_term),
                Farmer.mobile_number.ilike(search_term)
            ))
        
        if request.args.get('status'):
            query = query.filter(Farmer.verification_status == request.args.get('status'))
        
        if request.args.get('region'):
            query = query.filter(Farmer.region == request.args.get('region'))
        
        # Execute query with pagination
        farmers = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = {
            'farmers': [{
                'id': farmer.id,
                'rsbsa_id': farmer.rsbsa_id,
                'name': f"{farmer.first_name} {farmer.last_name}",
                'mobile_number': farmer.mobile_number,
                'region': farmer.region,
                'municipality': farmer.municipality,
                'verification_status': farmer.verification_status,
                'farming_experience_years': farmer.farming_experience_years,
                'card_bdsfi_member': farmer.card_bdsfi_member,
                'created_at': farmer.created_at.isoformat()
            } for farmer in farmers.items],
            'pagination': {
                'page': farmers.page,
                'pages': farmers.pages,
                'per_page': farmers.per_page,
                'total': farmers.total
            }
        }
        
        log_audit('list', 'farmers', details={'count': len(farmers.items)})
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching farmers: {str(e)}")
        return jsonify({'error': 'Failed to fetch farmers'}), 500

@agricultural_bp.route('/farmers', methods=['POST'])
@jwt_required()
@require_role(['super_admin', 'admin', 'manager', 'field_officer'])
def create_farmer():
    """Register a new farmer"""
    try:
        data = request.get_json()
        current_org = get_current_organization()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'mobile_number', 'region', 'municipality']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check for duplicate RSBSA ID if provided
        if data.get('rsbsa_id'):
            existing_farmer = Farmer.query.filter_by(rsbsa_id=data['rsbsa_id']).first()
            if existing_farmer:
                return jsonify({'error': 'RSBSA ID already exists'}), 400
        
        # Create farmer record
        farmer = Farmer(
            agricultural_org_id=current_org.id if current_org else None,
            rsbsa_id=data.get('rsbsa_id'),
            first_name=data['first_name'],
            middle_name=data.get('middle_name'),
            last_name=data['last_name'],
            suffix=data.get('suffix'),
            mobile_number=data['mobile_number'],
            email=data.get('email'),
            region=data['region'],
            province=data.get('province'),
            municipality=data['municipality'],
            barangay=data.get('barangay'),
            purok_sitio=data.get('purok_sitio'),
            zip_code=data.get('zip_code'),
            farming_experience_years=data.get('farming_experience_years'),
            primary_occupation=data.get('primary_occupation', 'Farmer'),
            secondary_occupation=data.get('secondary_occupation'),
            annual_income=data.get('annual_income'),
            card_bdsfi_member=data.get('card_bdsfi_member', False),
            card_member_id=data.get('card_member_id'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_number=data.get('emergency_contact_number'),
            emergency_contact_relationship=data.get('emergency_contact_relationship')
        )
        
        db.session.add(farmer)
        db.session.commit()
        
        log_audit('create', 'farmers', farmer.id, {
            'farmer_name': f"{farmer.first_name} {farmer.last_name}",
            'rsbsa_id': farmer.rsbsa_id
        })
        
        return jsonify({
            'message': 'Farmer registered successfully',
            'farmer_id': farmer.id,
            'rsbsa_id': farmer.rsbsa_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating farmer: {str(e)}")
        return jsonify({'error': 'Failed to register farmer'}), 500

@agricultural_bp.route('/farmers/<int:farmer_id>', methods=['GET'])
@jwt_required()
@require_role(['super_admin', 'admin', 'manager', 'field_officer', 'farmer'])
def get_farmer(farmer_id):
    """Get detailed farmer profile"""
    try:
        current_org = get_current_organization()
        current_user_id = get_jwt_identity()
        
        # Build query with organization filter
        query = Farmer.query.filter_by(id=farmer_id)
        if current_org:
            query = query.filter(Farmer.agricultural_org_id == current_org.id)
        
        farmer = query.first()
        if not farmer:
            return jsonify({'error': 'Farmer not found'}), 404
        
        # Check if user can access this farmer's data
        claims = get_jwt()
        user_role = claims.get('role')
        if user_role == 'farmer':
            # Farmers can only access their own profile
            if farmer.user_id != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Get farmer's farms
        farms = Farm.query.filter_by(farmer_id=farmer.id).all()
        
        result = {
            'id': farmer.id,
            'rsbsa_id': farmer.rsbsa_id,
            'farmer_id_card': farmer.farmer_id_card,
            'first_name': farmer.first_name,
            'middle_name': farmer.middle_name,
            'last_name': farmer.last_name,
            'suffix': farmer.suffix,
            'mobile_number': farmer.mobile_number,
            'email': farmer.email,
            'region': farmer.region,
            'province': farmer.province,
            'municipality': farmer.municipality,
            'barangay': farmer.barangay,
            'purok_sitio': farmer.purok_sitio,
            'zip_code': farmer.zip_code,
            'farming_experience_years': farmer.farming_experience_years,
            'primary_occupation': farmer.primary_occupation,
            'secondary_occupation': farmer.secondary_occupation,
            'annual_income': farmer.annual_income,
            'credit_score': farmer.credit_score,
            'card_bdsfi_member': farmer.card_bdsfi_member,
            'card_member_id': farmer.card_member_id,
            'emergency_contact_name': farmer.emergency_contact_name,
            'emergency_contact_number': farmer.emergency_contact_number,
            'emergency_contact_relationship': farmer.emergency_contact_relationship,
            'verification_status': farmer.verification_status,
            'is_active': farmer.is_active,
            'created_at': farmer.created_at.isoformat(),
            'farms': [{
                'id': farm.id,
                'farm_name': farm.farm_name,
                'total_area_hectares': farm.total_area_hectares,
                'farm_type': farm.farm_type.value,
                'municipality': farm.municipality,
                'barangay': farm.barangay
            } for farm in farms]
        }
        
        log_audit('view', 'farmers', farmer_id)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching farmer: {str(e)}")
        return jsonify({'error': 'Failed to fetch farmer details'}), 500

# Farm Management Routes
@agricultural_bp.route('/farms', methods=['GET'])
@jwt_required()
@require_role(['super_admin', 'admin', 'manager', 'field_officer'])
def get_farms():
    """Get list of farms with filtering"""
    try:
        current_org = get_current_organization()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query with organization filter
        query = Farm.query.join(Farmer)
        if current_org:
            query = query.filter(Farmer.agricultural_org_id == current_org.id)
        
        # Apply filters
        if request.args.get('farm_type'):
            query = query.filter(Farm.farm_type == request.args.get('farm_type'))
        
        if request.args.get('municipality'):
            query = query.filter(Farm.municipality == request.args.get('municipality'))
        
        # Execute query with pagination
        farms = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = {
            'farms': [{
                'id': farm.id,
                'farm_name': farm.farm_name,
                'farm_code': farm.farm_code,
                'farmer_name': f"{farm.farmer.first_name} {farm.farmer.last_name}",
                'total_area_hectares': farm.total_area_hectares,
                'farm_type': farm.farm_type.value,
                'municipality': farm.municipality,
                'barangay': farm.barangay,
                'is_active': farm.is_active,
                'created_at': farm.created_at.isoformat()
            } for farm in farms.items],
            'pagination': {
                'page': farms.page,
                'pages': farms.pages,
                'per_page': farms.per_page,
                'total': farms.total
            }
        }
        
        log_audit('list', 'farms', details={'count': len(farms.items)})
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching farms: {str(e)}")
        return jsonify({'error': 'Failed to fetch farms'}), 500

@agricultural_bp.route('/farms', methods=['POST'])
@jwt_required()
@require_role(['super_admin', 'admin', 'manager', 'field_officer'])
def create_farm():
    """Register a new farm"""
    try:
        data = request.get_json()
        current_org = get_current_organization()
        
        # Validate required fields
        required_fields = ['farmer_id', 'farm_name', 'total_area_hectares', 'farm_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate farmer exists and belongs to organization
        farmer = Farmer.query.filter_by(id=data['farmer_id']).first()
        if not farmer:
            return jsonify({'error': 'Farmer not found'}), 404
        
        if current_org and farmer.agricultural_org_id != current_org.id:
            return jsonify({'error': 'Farmer not in your organization'}), 403
        
        # Generate farm code if not provided
        farm_code = data.get('farm_code')
        if not farm_code:
            farm_code = f"FARM-{farmer.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create farm record
        farm = Farm(
            farmer_id=data['farmer_id'],
            agricultural_org_id=current_org.id if current_org else None,
            farm_name=data['farm_name'],
            farm_code=farm_code,
            region=data.get('region'),
            province=data.get('province'),
            municipality=data.get('municipality'),
            barangay=data.get('barangay'),
            purok_sitio=data.get('purok_sitio'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            elevation=data.get('elevation'),
            total_area_hectares=data['total_area_hectares'],
            cultivated_area_hectares=data.get('cultivated_area_hectares'),
            farm_type=FarmType(data['farm_type']),
            ownership_type=data.get('ownership_type'),
            land_title_number=data.get('land_title_number'),
            soil_type=data.get('soil_type'),
            water_source=data.get('water_source'),
            irrigation_type=data.get('irrigation_type'),
            has_storage=data.get('has_storage', False),
            has_drying_facility=data.get('has_drying_facility', False),
            has_machinery=data.get('has_machinery', False)
        )
        
        db.session.add(farm)
        db.session.commit()
        
        log_audit('create', 'farms', farm.id, {
            'farm_name': farm.farm_name,
            'farmer_name': f"{farmer.first_name} {farmer.last_name}",
            'area_hectares': farm.total_area_hectares
        })
        
        return jsonify({
            'message': 'Farm registered successfully',
            'farm_id': farm.id,
            'farm_code': farm.farm_code
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating farm: {str(e)}")
        return jsonify({'error': 'Failed to register farm'}), 500

# Agricultural Input Management Routes
@agricultural_bp.route('/inputs', methods=['GET'])
@jwt_required()
def get_agricultural_inputs():
    """Get agricultural inputs catalog"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query
        query = AgriculturalInput.query.filter_by(is_active=True)
        
        # Apply filters
        if request.args.get('input_type'):
            query = query.filter(AgriculturalInput.input_type == request.args.get('input_type'))
        
        if request.args.get('category'):
            query = query.filter(AgriculturalInput.category == request.args.get('category'))
        
        if request.args.get('search'):
            search_term = f"%{request.args.get('search')}%"
            query = query.filter(or_(
                AgriculturalInput.product_name.ilike(search_term),
                AgriculturalInput.brand.ilike(search_term),
                AgriculturalInput.description.ilike(search_term)
            ))
        
        # Execute query with pagination
        inputs = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = {
            'inputs': [{
                'id': input_item.id,
                'product_name': input_item.product_name,
                'brand': input_item.brand,
                'product_code': input_item.product_code,
                'input_type': input_item.input_type.value,
                'category': input_item.category,
                'description': input_item.description,
                'package_size': input_item.package_size,
                'unit_of_measure': input_item.unit_of_measure,
                'selling_price': input_item.selling_price,
                'application_rate': input_item.application_rate,
                'crop_suitability': input_item.crop_suitability,
                'stock_quantity': input_item.stock_quantity,
                'is_featured': input_item.is_featured
            } for input_item in inputs.items],
            'pagination': {
                'page': inputs.page,
                'pages': inputs.pages,
                'per_page': inputs.per_page,
                'total': inputs.total
            }
        }
        
        log_audit('list', 'agricultural_inputs', details={'count': len(inputs.items)})
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching agricultural inputs: {str(e)}")
        return jsonify({'error': 'Failed to fetch agricultural inputs'}), 500

# Farm Activity Tracking Routes
@agricultural_bp.route('/activities', methods=['POST'])
@jwt_required()
@require_role(['super_admin', 'admin', 'manager', 'field_officer', 'farmer'])
def record_farm_activity():
    """Record a farm activity"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        
        # Validate required fields
        required_fields = ['farmer_id', 'farm_id', 'activity_type', 'activity_name', 'activity_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate farmer and farm exist
        farmer = Farmer.query.get(data['farmer_id'])
        farm = Farm.query.get(data['farm_id'])
        
        if not farmer or not farm:
            return jsonify({'error': 'Farmer or farm not found'}), 404
        
        # Check permissions
        claims = get_jwt()
        user_role = claims.get('role')
        if user_role == 'farmer' and farmer.user_id != current_user_id:
            return jsonify({'error': 'Can only record activities for your own farm'}), 403
        
        # Parse activity date
        activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
        
        # Create activity record
        activity = FarmActivity(
            farmer_id=data['farmer_id'],
            farm_id=data['farm_id'],
            field_id=data.get('field_id'),
            activity_type=ActivityType(data['activity_type']),
            activity_name=data['activity_name'],
            activity_description=data.get('activity_description'),
            activity_date=activity_date,
            labor_hours=data.get('labor_hours'),
            labor_cost=data.get('labor_cost'),
            material_cost=data.get('material_cost'),
            equipment_used=data.get('equipment_used'),
            inputs_used=data.get('inputs_used'),
            area_covered_hectares=data.get('area_covered_hectares'),
            weather_conditions=data.get('weather_conditions'),
            results=data.get('results'),
            notes=data.get('notes'),
            photos=data.get('photos'),
            gps_coordinates=data.get('gps_coordinates')
        )
        
        db.session.add(activity)
        db.session.commit()
        
        log_audit('create', 'farm_activities', activity.id, {
            'activity_type': activity.activity_type.value,
            'farm_name': farm.farm_name,
            'farmer_name': f"{farmer.first_name} {farmer.last_name}"
        })
        
        return jsonify({
            'message': 'Farm activity recorded successfully',
            'activity_id': activity.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error recording farm activity: {str(e)}")
        return jsonify({'error': 'Failed to record farm activity'}), 500

# Dashboard and Analytics Routes
@agricultural_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
@require_role(['super_admin', 'admin', 'manager', 'field_officer'])
def get_dashboard_stats():
    """Get agricultural dashboard statistics"""
    try:
        current_org = get_current_organization()
        
        # Build base queries with organization filter
        farmers_query = Farmer.query
        farms_query = Farm.query.join(Farmer)
        activities_query = FarmActivity.query.join(Farmer)
        
        if current_org:
            farmers_query = farmers_query.filter(Farmer.agricultural_org_id == current_org.id)
            farms_query = farms_query.filter(Farmer.agricultural_org_id == current_org.id)
            activities_query = activities_query.filter(Farmer.agricultural_org_id == current_org.id)
        
        # Calculate statistics
        total_farmers = farmers_query.count()
        active_farmers = farmers_query.filter(Farmer.is_active == True).count()
        total_farms = farms_query.count()
        total_hectares = db.session.query(func.sum(Farm.total_area_hectares)).join(Farmer).filter(
            Farmer.agricultural_org_id == current_org.id if current_org else True
        ).scalar() or 0
        
        # Recent activities (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_activities = activities_query.filter(
            FarmActivity.activity_date >= thirty_days_ago.date()
        ).count()
        
        # Farm type distribution
        farm_types = db.session.query(
            Farm.farm_type,
            func.count(Farm.id).label('count')
        ).join(Farmer).filter(
            Farmer.agricultural_org_id == current_org.id if current_org else True
        ).group_by(Farm.farm_type).all()
        
        result = {
            'overview': {
                'total_farmers': total_farmers,
                'active_farmers': active_farmers,
                'total_farms': total_farms,
                'total_hectares': round(total_hectares, 2),
                'recent_activities': recent_activities
            },
            'farm_type_distribution': [
                {'type': farm_type.value, 'count': count}
                for farm_type, count in farm_types
            ]
        }
        
        log_audit('view', 'dashboard_stats')
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard stats: {str(e)}")
        return jsonify({'error': 'Failed to fetch dashboard statistics'}), 500

# Error handlers
@agricultural_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@agricultural_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
