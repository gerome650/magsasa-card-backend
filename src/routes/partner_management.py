"""
Partner management routes for API key administration and partner onboarding
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
import json

from src.models.user import db, User, Organization, UserRole
from src.models.partner_api import (
    PartnerAPIKey, PartnerIntegration, WebhookEvent, APIUsageLog,
    PartnerType, APIKeyStatus, RateLimiter
)
from src.routes.auth import require_permission, log_audit_event
from src.middleware.tenant import tenant_required, TenantContext

partner_mgmt_bp = Blueprint('partner_management', __name__)

@partner_mgmt_bp.route('/partner-management/api-keys', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def list_api_keys():
    """List API keys for current organization"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        
        if not organization_id:
            return jsonify({'error': 'Organization context required'}), 400
        
        # Query parameters
        partner_type = request.args.get('partner_type')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query
        query = PartnerAPIKey.query.filter_by(organization_id=organization_id)
        
        if partner_type:
            try:
                partner_type_enum = PartnerType(partner_type)
                query = query.filter_by(partner_type=partner_type_enum)
            except ValueError:
                return jsonify({'error': 'Invalid partner type'}), 400
        
        if status:
            try:
                status_enum = APIKeyStatus(status)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        # Pagination
        total = query.count()
        api_keys = query.order_by(PartnerAPIKey.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Convert to dict
        api_keys_data = [key.to_dict() for key in api_keys]
        
        log_audit_event(
            action='PARTNER_API_KEYS_LISTED',
            resource='partner_api_key',
            details={'organization_id': organization_id, 'count': len(api_keys_data)},
            user_id=current_user_id
        )
        
        return jsonify({
            'api_keys': api_keys_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"List API keys error: {str(e)}")
        return jsonify({'error': 'Failed to list API keys'}), 500

@partner_mgmt_bp.route('/partner-management/api-keys', methods=['POST'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def create_api_key():
    """Create a new API key for partner"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        data = request.get_json()
        
        if not organization_id:
            return jsonify({'error': 'Organization context required'}), 400
        
        # Validate required fields
        required_fields = ['key_name', 'partner_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate partner type
        try:
            partner_type = PartnerType(data['partner_type'])
        except ValueError:
            return jsonify({'error': 'Invalid partner type'}), 400
        
        # Check if key name already exists for this organization
        existing_key = PartnerAPIKey.query.filter_by(
            organization_id=organization_id,
            key_name=data['key_name']
        ).first()
        
        if existing_key:
            return jsonify({'error': 'API key name already exists'}), 409
        
        # Create API key
        api_key = PartnerAPIKey(
            organization_id=organization_id,
            partner_type=partner_type,
            key_name=data['key_name'],
            rate_limit_per_minute=data.get('rate_limit_per_minute', 60),
            rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
            rate_limit_per_day=data.get('rate_limit_per_day', 10000),
            expires_at=datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00')) if data.get('expires_at') else None,
            allowed_endpoints=json.dumps(data.get('allowed_endpoints', [])) if data.get('allowed_endpoints') else None,
            ip_whitelist=json.dumps(data.get('ip_whitelist', [])) if data.get('ip_whitelist') else None
        )
        
        # Generate the actual API key (this is only shown once)
        full_api_key = PartnerAPIKey.generate_api_key()
        api_key.key_prefix = full_api_key[:8]
        api_key.key_hash = PartnerAPIKey.hash_key(full_api_key)
        
        db.session.add(api_key)
        db.session.commit()
        
        log_audit_event(
            action='PARTNER_API_KEY_CREATED',
            resource='partner_api_key',
            resource_id=api_key.id,
            details={
                'key_name': data['key_name'],
                'partner_type': partner_type.value,
                'organization_id': organization_id
            },
            user_id=current_user_id
        )
        
        # Return the API key data including the full key (only time it's shown)
        response_data = api_key.to_dict()
        response_data['api_key'] = full_api_key  # Only shown once
        
        return jsonify({
            'message': 'API key created successfully',
            'api_key_data': response_data,
            'warning': 'Save the API key securely. It will not be shown again.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create API key error: {str(e)}")
        return jsonify({'error': 'Failed to create API key'}), 500

@partner_mgmt_bp.route('/partner-management/api-keys/<int:key_id>', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def get_api_key(key_id):
    """Get API key details"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        
        api_key = PartnerAPIKey.query.filter_by(
            id=key_id,
            organization_id=organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Get usage statistics
        rate_limit_status = RateLimiter.get_rate_limit_status(api_key)
        
        # Get recent usage logs
        recent_logs = APIUsageLog.query.filter_by(
            api_key_id=api_key.id
        ).order_by(APIUsageLog.timestamp.desc()).limit(10).all()
        
        api_key_data = api_key.to_dict(include_sensitive=True)
        api_key_data['rate_limit_status'] = rate_limit_status
        api_key_data['recent_usage'] = [log.to_dict() for log in recent_logs]
        
        log_audit_event(
            action='PARTNER_API_KEY_VIEWED',
            resource='partner_api_key',
            resource_id=key_id,
            user_id=current_user_id
        )
        
        return jsonify({'api_key': api_key_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get API key error: {str(e)}")
        return jsonify({'error': 'Failed to get API key'}), 500

@partner_mgmt_bp.route('/partner-management/api-keys/<int:key_id>', methods=['PUT'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def update_api_key(key_id):
    """Update API key settings"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        data = request.get_json()
        
        api_key = PartnerAPIKey.query.filter_by(
            id=key_id,
            organization_id=organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Update allowed fields
        updatable_fields = [
            'key_name', 'rate_limit_per_minute', 'rate_limit_per_hour', 
            'rate_limit_per_day', 'expires_at', 'allowed_endpoints', 'ip_whitelist'
        ]
        
        updated_fields = []
        for field in updatable_fields:
            if field in data:
                if field == 'expires_at' and data[field]:
                    setattr(api_key, field, datetime.fromisoformat(data[field].replace('Z', '+00:00')))
                elif field in ['allowed_endpoints', 'ip_whitelist'] and data[field]:
                    setattr(api_key, field, json.dumps(data[field]))
                else:
                    setattr(api_key, field, data[field])
                updated_fields.append(field)
        
        db.session.commit()
        
        log_audit_event(
            action='PARTNER_API_KEY_UPDATED',
            resource='partner_api_key',
            resource_id=key_id,
            details={'updated_fields': updated_fields},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'API key updated successfully',
            'api_key': api_key.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update API key error: {str(e)}")
        return jsonify({'error': 'Failed to update API key'}), 500

@partner_mgmt_bp.route('/partner-management/api-keys/<int:key_id>/revoke', methods=['POST'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def revoke_api_key(key_id):
    """Revoke an API key"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        data = request.get_json() or {}
        
        api_key = PartnerAPIKey.query.filter_by(
            id=key_id,
            organization_id=organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        if api_key.status == APIKeyStatus.REVOKED:
            return jsonify({'error': 'API key is already revoked'}), 400
        
        # Revoke the key
        reason = data.get('reason', 'Revoked by administrator')
        api_key.revoke(current_user_id, reason)
        
        db.session.commit()
        
        log_audit_event(
            action='PARTNER_API_KEY_REVOKED',
            resource='partner_api_key',
            resource_id=key_id,
            details={'reason': reason},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'API key revoked successfully',
            'api_key': api_key.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Revoke API key error: {str(e)}")
        return jsonify({'error': 'Failed to revoke API key'}), 500

@partner_mgmt_bp.route('/partner-management/integrations', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def list_partner_integrations():
    """List partner integrations"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        
        integrations = PartnerIntegration.query.filter_by(
            organization_id=organization_id
        ).order_by(PartnerIntegration.created_at.desc()).all()
        
        integrations_data = [integration.to_dict() for integration in integrations]
        
        log_audit_event(
            action='PARTNER_INTEGRATIONS_LISTED',
            resource='partner_integration',
            details={'organization_id': organization_id, 'count': len(integrations_data)},
            user_id=current_user_id
        )
        
        return jsonify({'integrations': integrations_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"List integrations error: {str(e)}")
        return jsonify({'error': 'Failed to list integrations'}), 500

@partner_mgmt_bp.route('/partner-management/integrations', methods=['POST'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def create_partner_integration():
    """Create a new partner integration"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['integration_name', 'partner_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate partner type
        try:
            partner_type = PartnerType(data['partner_type'])
        except ValueError:
            return jsonify({'error': 'Invalid partner type'}), 400
        
        # Create integration
        integration = PartnerIntegration(
            organization_id=organization_id,
            partner_type=partner_type,
            integration_name=data['integration_name'],
            description=data.get('description'),
            webhook_url=data.get('webhook_url'),
            callback_url=data.get('callback_url'),
            sync_enabled=data.get('sync_enabled', False),
            sync_frequency=data.get('sync_frequency', 'hourly'),
            commission_rate=data.get('commission_rate', 0.0),
            minimum_order_value=data.get('minimum_order_value', 0.0),
            maximum_order_value=data.get('maximum_order_value')
        )
        
        db.session.add(integration)
        db.session.commit()
        
        log_audit_event(
            action='PARTNER_INTEGRATION_CREATED',
            resource='partner_integration',
            resource_id=integration.id,
            details={
                'integration_name': data['integration_name'],
                'partner_type': partner_type.value
            },
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Partner integration created successfully',
            'integration': integration.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create integration error: {str(e)}")
        return jsonify({'error': 'Failed to create integration'}), 500

@partner_mgmt_bp.route('/partner-management/analytics/overview', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def get_partner_analytics_overview():
    """Get partner analytics overview"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        
        # Get API key statistics
        total_api_keys = PartnerAPIKey.query.filter_by(organization_id=organization_id).count()
        active_api_keys = PartnerAPIKey.query.filter_by(
            organization_id=organization_id,
            status=APIKeyStatus.ACTIVE
        ).count()
        
        # Get usage statistics (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        total_requests = db.session.query(APIUsageLog).join(PartnerAPIKey).filter(
            PartnerAPIKey.organization_id == organization_id,
            APIUsageLog.timestamp >= thirty_days_ago
        ).count()
        
        successful_requests = db.session.query(APIUsageLog).join(PartnerAPIKey).filter(
            PartnerAPIKey.organization_id == organization_id,
            APIUsageLog.timestamp >= thirty_days_ago,
            APIUsageLog.status_code < 400
        ).count()
        
        # Get partner type distribution
        partner_type_stats = db.session.query(
            PartnerAPIKey.partner_type,
            db.func.count(PartnerAPIKey.id).label('count')
        ).filter_by(organization_id=organization_id).group_by(
            PartnerAPIKey.partner_type
        ).all()
        
        partner_type_distribution = {
            partner_type.value: count for partner_type, count in partner_type_stats
        }
        
        # Get top endpoints
        top_endpoints = db.session.query(
            APIUsageLog.endpoint,
            db.func.count(APIUsageLog.id).label('count')
        ).join(PartnerAPIKey).filter(
            PartnerAPIKey.organization_id == organization_id,
            APIUsageLog.timestamp >= thirty_days_ago
        ).group_by(APIUsageLog.endpoint).order_by(
            db.func.count(APIUsageLog.id).desc()
        ).limit(10).all()
        
        analytics_overview = {
            'api_keys': {
                'total': total_api_keys,
                'active': active_api_keys,
                'inactive': total_api_keys - active_api_keys
            },
            'usage_30_days': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0
            },
            'partner_type_distribution': partner_type_distribution,
            'top_endpoints': [
                {'endpoint': endpoint, 'requests': count}
                for endpoint, count in top_endpoints
            ],
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        log_audit_event(
            action='PARTNER_ANALYTICS_VIEWED',
            resource='partner_analytics',
            details={'organization_id': organization_id},
            user_id=current_user_id
        )
        
        return jsonify({'analytics': analytics_overview}), 200
        
    except Exception as e:
        current_app.logger.error(f"Partner analytics error: {str(e)}")
        return jsonify({'error': 'Failed to get partner analytics'}), 500

@partner_mgmt_bp.route('/partner-management/webhooks', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
@require_permission('partner.manage')
def list_webhook_events():
    """List webhook events for partner integrations"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        
        # Query parameters
        status = request.args.get('status')
        event_type = request.args.get('event_type')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query
        query = db.session.query(WebhookEvent).join(PartnerIntegration).filter(
            PartnerIntegration.organization_id == organization_id
        )
        
        if status:
            query = query.filter(WebhookEvent.status == status)
        
        if event_type:
            query = query.filter(WebhookEvent.event_type == event_type)
        
        # Pagination
        total = query.count()
        webhook_events = query.order_by(WebhookEvent.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        events_data = [event.to_dict() for event in webhook_events]
        
        log_audit_event(
            action='WEBHOOK_EVENTS_LISTED',
            resource='webhook_event',
            details={'organization_id': organization_id, 'count': len(events_data)},
            user_id=current_user_id
        )
        
        return jsonify({
            'webhook_events': events_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"List webhook events error: {str(e)}")
        return jsonify({'error': 'Failed to list webhook events'}), 500
