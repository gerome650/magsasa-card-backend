"""
Multi-tenant middleware for automatic organization context injection and data isolation
"""

from flask import request, g, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from functools import wraps
import threading

from src.models.user import User, Organization, UserRole

# Thread-local storage for tenant context
_tenant_context = threading.local()

class TenantContext:
    """Thread-local tenant context manager"""
    
    @staticmethod
    def set_organization(organization_id, organization=None):
        """Set the current organization context"""
        _tenant_context.organization_id = organization_id
        _tenant_context.organization = organization
    
    @staticmethod
    def get_organization_id():
        """Get the current organization ID"""
        return getattr(_tenant_context, 'organization_id', None)
    
    @staticmethod
    def get_organization():
        """Get the current organization object"""
        return getattr(_tenant_context, 'organization', None)
    
    @staticmethod
    def clear():
        """Clear the tenant context"""
        _tenant_context.organization_id = None
        _tenant_context.organization = None
    
    @staticmethod
    def set_user(user_id, user=None):
        """Set the current user context"""
        _tenant_context.user_id = user_id
        _tenant_context.user = user
    
    @staticmethod
    def get_user_id():
        """Get the current user ID"""
        return getattr(_tenant_context, 'user_id', None)
    
    @staticmethod
    def get_user():
        """Get the current user object"""
        return getattr(_tenant_context, 'user', None)

def tenant_required(allow_cross_tenant=False):
    """
    Decorator to enforce tenant context for API endpoints
    
    Args:
        allow_cross_tenant (bool): Allow super admins to access cross-tenant data
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verify JWT token
                verify_jwt_in_request()
                current_user_id = get_jwt_identity()
                
                if not current_user_id:
                    return jsonify({'error': 'Authentication required'}), 401
                
                # Get current user
                user = User.query.get(current_user_id)
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                # Set user context
                TenantContext.set_user(current_user_id, user)
                
                # Determine organization context
                organization_id = None
                
                # Check for organization_id in request
                if request.method in ['POST', 'PUT', 'PATCH']:
                    data = request.get_json() or {}
                    organization_id = data.get('organization_id')
                elif request.method == 'GET':
                    organization_id = request.args.get('organization_id', type=int)
                
                # If no organization specified, use user's primary organization
                if not organization_id:
                    primary_org = user.get_primary_organization()
                    if primary_org:
                        organization_id = primary_org.id
                
                # Validate organization access
                if organization_id:
                    organization = Organization.query.get(organization_id)
                    if not organization:
                        return jsonify({'error': 'Organization not found'}), 404
                    
                    # Check if user has access to this organization
                    user_role = user.get_role_in_organization(organization_id)
                    is_super_admin = any(
                        user.get_role_in_organization(org.id) == UserRole.SUPER_ADMIN
                        for org in user.organizations
                    )
                    
                    if not user_role and not (allow_cross_tenant and is_super_admin):
                        return jsonify({'error': 'Access denied to organization'}), 403
                    
                    # Set organization context
                    TenantContext.set_organization(organization_id, organization)
                
                # Store in Flask's g object for backward compatibility
                g.current_user = user
                g.current_organization_id = organization_id
                g.current_organization = TenantContext.get_organization()
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Tenant middleware error: {str(e)}")
                return jsonify({'error': 'Tenant context error'}), 500
            finally:
                # Clear context after request
                TenantContext.clear()
        
        return decorated_function
    return decorator

def organization_scoped_query(model_class, organization_field='organization_id'):
    """
    Create an organization-scoped query for a model
    
    Args:
        model_class: SQLAlchemy model class
        organization_field: Field name that contains organization ID
    
    Returns:
        Scoped query object
    """
    from src.models.user import db
    
    query = model_class.query
    organization_id = TenantContext.get_organization_id()
    
    if organization_id and hasattr(model_class, organization_field):
        query = query.filter(getattr(model_class, organization_field) == organization_id)
    
    return query

class TenantAwareModel:
    """Mixin class for tenant-aware models"""
    
    @classmethod
    def tenant_query(cls, organization_field='organization_id'):
        """Get a tenant-scoped query for this model"""
        return organization_scoped_query(cls, organization_field)
    
    def is_accessible_by_current_tenant(self, organization_field='organization_id'):
        """Check if this record is accessible by the current tenant"""
        current_org_id = TenantContext.get_organization_id()
        if not current_org_id:
            return False
        
        record_org_id = getattr(self, organization_field, None)
        return record_org_id == current_org_id
    
    def ensure_tenant_access(self, organization_field='organization_id'):
        """Ensure the current tenant has access to this record"""
        if not self.is_accessible_by_current_tenant(organization_field):
            from flask import abort
            abort(403)

def init_tenant_middleware(app):
    """Initialize tenant middleware with Flask app"""
    
    @app.before_request
    def before_request():
        """Clear tenant context before each request"""
        TenantContext.clear()
    
    @app.after_request
    def after_request(response):
        """Clear tenant context after each request"""
        TenantContext.clear()
        return response
    
    @app.teardown_request
    def teardown_request(exception):
        """Clear tenant context on request teardown"""
        TenantContext.clear()

def get_tenant_stats():
    """Get statistics for the current tenant"""
    organization_id = TenantContext.get_organization_id()
    organization = TenantContext.get_organization()
    
    if not organization_id or not organization:
        return None
    
    from src.models.user import db, AuditLog
    from datetime import datetime, timedelta, timezone
    
    # Calculate various statistics
    stats = {
        'organization_id': organization_id,
        'organization_name': organization.name,
        'organization_type': organization.type,
        'total_users': len(organization.users),
        'active_users': len([u for u in organization.users if u.status.value == 'active']),
    }
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_activity = AuditLog.query.filter(
        AuditLog.organization_id == organization_id,
        AuditLog.timestamp >= thirty_days_ago
    ).count()
    stats['recent_activity_count'] = recent_activity
    
    # User role distribution
    role_distribution = {}
    for user in organization.users:
        role = user.get_role_in_organization(organization_id)
        if role:
            role_name = role.value
            role_distribution[role_name] = role_distribution.get(role_name, 0) + 1
    stats['role_distribution'] = role_distribution
    
    return stats

def validate_cross_tenant_access(target_organization_id):
    """
    Validate if current user can access data from another organization
    
    Args:
        target_organization_id: ID of the target organization
    
    Returns:
        bool: True if access is allowed, False otherwise
    """
    current_user = TenantContext.get_user()
    if not current_user:
        return False
    
    # Super admins can access any organization
    is_super_admin = any(
        current_user.get_role_in_organization(org.id) == UserRole.SUPER_ADMIN
        for org in current_user.organizations
    )
    
    if is_super_admin:
        return True
    
    # Check if user has any role in the target organization
    target_role = current_user.get_role_in_organization(target_organization_id)
    return target_role is not None

def enforce_tenant_isolation(query, model_class, organization_field='organization_id'):
    """
    Enforce tenant isolation on a query
    
    Args:
        query: SQLAlchemy query object
        model_class: Model class being queried
        organization_field: Field name containing organization ID
    
    Returns:
        Modified query with tenant isolation
    """
    organization_id = TenantContext.get_organization_id()
    
    if organization_id and hasattr(model_class, organization_field):
        query = query.filter(getattr(model_class, organization_field) == organization_id)
    
    return query

class TenantAwareQueryMixin:
    """Mixin to add tenant-aware query methods to models"""
    
    @classmethod
    def get_for_current_tenant(cls, **filters):
        """Get records for the current tenant with optional filters"""
        query = organization_scoped_query(cls)
        
        for field, value in filters.items():
            if hasattr(cls, field):
                query = query.filter(getattr(cls, field) == value)
        
        return query
    
    @classmethod
    def count_for_current_tenant(cls, **filters):
        """Count records for the current tenant"""
        return cls.get_for_current_tenant(**filters).count()
    
    @classmethod
    def create_for_current_tenant(cls, **kwargs):
        """Create a new record for the current tenant"""
        organization_id = TenantContext.get_organization_id()
        if organization_id and 'organization_id' not in kwargs:
            kwargs['organization_id'] = organization_id
        
        from src.models.user import db
        instance = cls(**kwargs)
        db.session.add(instance)
        return instance
