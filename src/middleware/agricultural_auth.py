"""
MAGSASA-CARD Enhanced Platform - Agricultural Authorization Middleware
Advanced middleware for agricultural operation authorization and data access control
"""

from functools import wraps
from flask import request, jsonify, current_app, g
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from typing import List, Optional, Dict, Any
import json

from src.models.agricultural_permissions import (
    agricultural_role_manager, 
    AgriculturalPermission,
    get_agricultural_permissions_for_user,
    check_agricultural_permission
)
from src.middleware.tenant import get_current_organization

class AgriculturalAuthorizationError(Exception):
    """Custom exception for agricultural authorization errors"""
    pass

class DataAccessLevel:
    """Data access level constants"""
    OWN = 'own'
    ASSIGNED = 'assigned'
    ORGANIZATION = 'organization'
    PARTNER = 'partner'
    ALL = 'all'

def require_agricultural_permission(permissions: List[str], data_access_check: bool = True):
    """
    Decorator to require specific agricultural permissions
    
    Args:
        permissions: List of required permissions
        data_access_check: Whether to perform data access level validation
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verify JWT token
                verify_jwt_in_request()
                
                # Get user information
                current_user_id = get_jwt_identity()
                claims = get_jwt()
                user_role = claims.get('role')
                user_org_id = claims.get('organization_id')
                
                if not user_role:
                    return jsonify({'error': 'User role not found in token'}), 401
                
                # Check if user has required permissions
                user_permissions = get_agricultural_permissions_for_user(user_role)
                
                # Check each required permission
                missing_permissions = []
                for permission in permissions:
                    if permission not in user_permissions:
                        missing_permissions.append(permission)
                
                if missing_permissions:
                    current_app.logger.warning(
                        f"User {current_user_id} with role {user_role} missing permissions: {missing_permissions}"
                    )
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'required_permissions': permissions,
                        'missing_permissions': missing_permissions
                    }), 403
                
                # Perform data access level check if required
                if data_access_check:
                    access_result = check_data_access_level(
                        user_role, user_id=current_user_id, 
                        organization_id=user_org_id, **kwargs
                    )
                    if not access_result['allowed']:
                        return jsonify({
                            'error': 'Data access denied',
                            'reason': access_result['reason']
                        }), 403
                
                # Store user context for use in the route
                g.current_user_id = current_user_id
                g.current_user_role = user_role
                g.current_user_org_id = user_org_id
                g.user_permissions = user_permissions
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Agricultural authorization error: {str(e)}")
                return jsonify({'error': 'Authorization failed'}), 500
        
        return decorated_function
    return decorator

def check_data_access_level(user_role: str, user_id: int = None, 
                          organization_id: int = None, **kwargs) -> Dict[str, Any]:
    """
    Check if user has appropriate data access level for the requested operation
    
    Args:
        user_role: User's role
        user_id: Current user ID
        organization_id: User's organization ID
        **kwargs: Additional parameters from route (e.g., farmer_id, farm_id)
    
    Returns:
        Dict with 'allowed' boolean and 'reason' string
    """
    try:
        # Get role configuration
        role = agricultural_role_manager.get_role(user_role)
        if not role:
            return {'allowed': False, 'reason': 'Invalid user role'}
        
        data_access_level = role.data_access_level
        organization_scope = role.organization_scope
        
        # Super admin and system roles have full access
        if data_access_level == DataAccessLevel.ALL:
            return {'allowed': True, 'reason': 'Full system access'}
        
        # Check organization-level access
        if data_access_level == DataAccessLevel.ORGANIZATION:
            current_org = get_current_organization()
            if not current_org:
                return {'allowed': False, 'reason': 'No organization context'}
            
            # For organization-level access, user must be in the same organization
            if organization_id and current_org.id != organization_id:
                return {'allowed': False, 'reason': 'Cross-organization access denied'}
            
            return {'allowed': True, 'reason': 'Organization-level access granted'}
        
        # Check partner-level access
        if data_access_level == DataAccessLevel.PARTNER:
            # Partners can access data related to their operations
            # This would typically involve checking partner relationships
            return {'allowed': True, 'reason': 'Partner access granted'}
        
        # Check assigned-level access (for field officers)
        if data_access_level == DataAccessLevel.ASSIGNED:
            # Field officers can access farmers/farms assigned to them
            # This would involve checking assignment relationships
            return {'allowed': True, 'reason': 'Assigned data access granted'}
        
        # Check own-level access (for farmers)
        if data_access_level == DataAccessLevel.OWN:
            # Farmers can only access their own data
            farmer_id = kwargs.get('farmer_id')
            farm_id = kwargs.get('farm_id')
            
            if farmer_id or farm_id:
                # Check if the farmer/farm belongs to the current user
                # This would involve database queries to verify ownership
                return check_ownership_access(user_id, farmer_id, farm_id)
            
            return {'allowed': True, 'reason': 'Own data access granted'}
        
        return {'allowed': False, 'reason': 'Unknown data access level'}
        
    except Exception as e:
        current_app.logger.error(f"Data access level check error: {str(e)}")
        return {'allowed': False, 'reason': 'Access check failed'}

def check_ownership_access(user_id: int, farmer_id: int = None, 
                         farm_id: int = None) -> Dict[str, Any]:
    """
    Check if user owns the requested farmer/farm data
    
    Args:
        user_id: Current user ID
        farmer_id: Requested farmer ID
        farm_id: Requested farm ID
    
    Returns:
        Dict with 'allowed' boolean and 'reason' string
    """
    try:
        # Import here to avoid circular imports
        from src.models.agricultural import Farmer, Farm
        
        # Check farmer ownership
        if farmer_id:
            farmer = Farmer.query.filter_by(id=farmer_id, user_id=user_id).first()
            if not farmer:
                return {'allowed': False, 'reason': 'Farmer data not owned by user'}
        
        # Check farm ownership
        if farm_id:
            if farmer_id:
                # Farm must belong to the specified farmer
                farm = Farm.query.filter_by(id=farm_id, farmer_id=farmer_id).first()
            else:
                # Check if farm belongs to any farmer owned by the user
                farm = Farm.query.join(Farmer).filter(
                    Farm.id == farm_id,
                    Farmer.user_id == user_id
                ).first()
            
            if not farm:
                return {'allowed': False, 'reason': 'Farm data not owned by user'}
        
        return {'allowed': True, 'reason': 'Ownership verified'}
        
    except Exception as e:
        current_app.logger.error(f"Ownership check error: {str(e)}")
        return {'allowed': False, 'reason': 'Ownership verification failed'}

def get_user_data_filter(user_role: str, user_id: int = None, 
                        organization_id: int = None) -> Dict[str, Any]:
    """
    Get data filtering parameters based on user role and access level
    
    Args:
        user_role: User's role
        user_id: Current user ID
        organization_id: User's organization ID
    
    Returns:
        Dict with filtering parameters for database queries
    """
    role = agricultural_role_manager.get_role(user_role)
    if not role:
        return {'filter_type': 'none'}
    
    data_access_level = role.data_access_level
    
    if data_access_level == DataAccessLevel.ALL:
        return {'filter_type': 'none'}  # No filtering needed
    
    elif data_access_level == DataAccessLevel.ORGANIZATION:
        current_org = get_current_organization()
        return {
            'filter_type': 'organization',
            'organization_id': current_org.id if current_org else None
        }
    
    elif data_access_level == DataAccessLevel.OWN:
        return {
            'filter_type': 'user',
            'user_id': user_id
        }
    
    elif data_access_level == DataAccessLevel.ASSIGNED:
        return {
            'filter_type': 'assigned',
            'user_id': user_id,
            'organization_id': organization_id
        }
    
    elif data_access_level == DataAccessLevel.PARTNER:
        return {
            'filter_type': 'partner',
            'user_id': user_id
        }
    
    return {'filter_type': 'none'}

def apply_data_filter(query, filter_params: Dict[str, Any], model_class):
    """
    Apply data filtering to a SQLAlchemy query based on filter parameters
    
    Args:
        query: SQLAlchemy query object
        filter_params: Filter parameters from get_user_data_filter
        model_class: The model class being queried
    
    Returns:
        Filtered query object
    """
    filter_type = filter_params.get('filter_type')
    
    if filter_type == 'none':
        return query
    
    elif filter_type == 'organization':
        org_id = filter_params.get('organization_id')
        if org_id and hasattr(model_class, 'agricultural_org_id'):
            return query.filter(model_class.agricultural_org_id == org_id)
    
    elif filter_type == 'user':
        user_id = filter_params.get('user_id')
        if user_id and hasattr(model_class, 'user_id'):
            return query.filter(model_class.user_id == user_id)
    
    elif filter_type == 'assigned':
        # For assigned access, implement specific logic based on assignments
        # This would involve joining with assignment tables
        pass
    
    elif filter_type == 'partner':
        # For partner access, implement partner-specific filtering
        # This would involve partner relationship tables
        pass
    
    return query

# Convenience decorators for common agricultural permissions

def require_farmer_access(access_level: str = 'view'):
    """Require farmer access permissions"""
    permission_map = {
        'view': [AgriculturalPermission.FARMER_VIEW_ALL.value],
        'create': [AgriculturalPermission.FARMER_CREATE.value],
        'update': [AgriculturalPermission.FARMER_UPDATE_ALL.value],
        'delete': [AgriculturalPermission.FARMER_DELETE.value]
    }
    permissions = permission_map.get(access_level, [AgriculturalPermission.FARMER_VIEW_ALL.value])
    return require_agricultural_permission(permissions)

def require_farm_access(access_level: str = 'view'):
    """Require farm access permissions"""
    permission_map = {
        'view': [AgriculturalPermission.FARM_VIEW_ALL.value],
        'create': [AgriculturalPermission.FARM_CREATE.value],
        'update': [AgriculturalPermission.FARM_UPDATE_ALL.value],
        'delete': [AgriculturalPermission.FARM_DELETE.value]
    }
    permissions = permission_map.get(access_level, [AgriculturalPermission.FARM_VIEW_ALL.value])
    return require_agricultural_permission(permissions)

def require_activity_access(access_level: str = 'view'):
    """Require farm activity access permissions"""
    permission_map = {
        'view': [AgriculturalPermission.ACTIVITY_VIEW_ALL.value],
        'create': [AgriculturalPermission.ACTIVITY_CREATE.value],
        'update': [AgriculturalPermission.ACTIVITY_UPDATE_ALL.value],
        'approve': [AgriculturalPermission.ACTIVITY_APPROVE.value]
    }
    permissions = permission_map.get(access_level, [AgriculturalPermission.ACTIVITY_VIEW_ALL.value])
    return require_agricultural_permission(permissions)

def require_input_access(access_level: str = 'view'):
    """Require agricultural input access permissions"""
    permission_map = {
        'view': [AgriculturalPermission.INPUT_VIEW_CATALOG.value],
        'create': [AgriculturalPermission.INPUT_CREATE.value],
        'update': [AgriculturalPermission.INPUT_UPDATE.value],
        'manage': [AgriculturalPermission.INPUT_MANAGE_STOCK.value, AgriculturalPermission.INPUT_MANAGE_PRICING.value]
    }
    permissions = permission_map.get(access_level, [AgriculturalPermission.INPUT_VIEW_CATALOG.value])
    return require_agricultural_permission(permissions)

def require_analytics_access(access_level: str = 'basic'):
    """Require analytics access permissions"""
    permission_map = {
        'basic': [AgriculturalPermission.ANALYTICS_VIEW_BASIC.value],
        'advanced': [AgriculturalPermission.ANALYTICS_VIEW_ADVANCED.value],
        'financial': [AgriculturalPermission.ANALYTICS_VIEW_FINANCIAL.value]
    }
    permissions = permission_map.get(access_level, [AgriculturalPermission.ANALYTICS_VIEW_BASIC.value])
    return require_agricultural_permission(permissions)

def require_mobile_access():
    """Require mobile field operations access"""
    permissions = [
        AgriculturalPermission.MOBILE_FIELD_OPERATIONS.value,
        AgriculturalPermission.MOBILE_OFFLINE_SYNC.value
    ]
    return require_agricultural_permission(permissions)

def require_card_access(access_level: str = 'view'):
    """Require CARD BDSFI integration access"""
    permission_map = {
        'view': [AgriculturalPermission.CARD_VIEW_MEMBERS.value],
        'update': [AgriculturalPermission.CARD_UPDATE_MEMBERS.value],
        'financial': [AgriculturalPermission.CARD_VIEW_FINANCIALS.value],
        'loans': [AgriculturalPermission.CARD_MANAGE_LOANS.value]
    }
    permissions = permission_map.get(access_level, [AgriculturalPermission.CARD_VIEW_MEMBERS.value])
    return require_agricultural_permission(permissions)
