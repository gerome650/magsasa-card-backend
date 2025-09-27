from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from src.models.user import (
    db, User, Permission, UserRole, AuditLog
)
from src.routes.auth import require_permission, log_audit_event

permission_bp = Blueprint('permission', __name__)

# Default permissions for each role
DEFAULT_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [
        # System administration
        {'name': 'system.admin', 'resource': 'system', 'action': 'admin', 'description': 'Full system administration access'},
        {'name': 'user.create', 'resource': 'user', 'action': 'create', 'description': 'Create new users'},
        {'name': 'user.read', 'resource': 'user', 'action': 'read', 'description': 'View user information'},
        {'name': 'user.update', 'resource': 'user', 'action': 'update', 'description': 'Update user information'},
        {'name': 'user.delete', 'resource': 'user', 'action': 'delete', 'description': 'Delete users'},
        {'name': 'organization.create', 'resource': 'organization', 'action': 'create', 'description': 'Create organizations'},
        {'name': 'organization.read', 'resource': 'organization', 'action': 'read', 'description': 'View organization information'},
        {'name': 'organization.update', 'resource': 'organization', 'action': 'update', 'description': 'Update organization information'},
        {'name': 'organization.delete', 'resource': 'organization', 'action': 'delete', 'description': 'Delete organizations'},
        {'name': 'organization.manage_users', 'resource': 'organization', 'action': 'manage_users', 'description': 'Manage organization users'},
        {'name': 'permission.manage', 'resource': 'permission', 'action': 'manage', 'description': 'Manage permissions'},
        {'name': 'audit.read', 'resource': 'audit', 'action': 'read', 'description': 'View audit logs'},
        {'name': 'report.create', 'resource': 'report', 'action': 'create', 'description': 'Create reports'},
        {'name': 'report.read', 'resource': 'report', 'action': 'read', 'description': 'View reports'},
        {'name': 'api.access', 'resource': 'api', 'action': 'access', 'description': 'Access API endpoints'},
    ],
    UserRole.ADMIN: [
        # Organization administration
        {'name': 'user.create', 'resource': 'user', 'action': 'create', 'description': 'Create new users'},
        {'name': 'user.read', 'resource': 'user', 'action': 'read', 'description': 'View user information'},
        {'name': 'user.update', 'resource': 'user', 'action': 'update', 'description': 'Update user information'},
        {'name': 'organization.read', 'resource': 'organization', 'action': 'read', 'description': 'View organization information'},
        {'name': 'organization.update', 'resource': 'organization', 'action': 'update', 'description': 'Update organization information'},
        {'name': 'organization.manage_users', 'resource': 'organization', 'action': 'manage_users', 'description': 'Manage organization users'},
        {'name': 'farm.create', 'resource': 'farm', 'action': 'create', 'description': 'Create farm records'},
        {'name': 'farm.read', 'resource': 'farm', 'action': 'read', 'description': 'View farm information'},
        {'name': 'farm.update', 'resource': 'farm', 'action': 'update', 'description': 'Update farm information'},
        {'name': 'farm.delete', 'resource': 'farm', 'action': 'delete', 'description': 'Delete farm records'},
        {'name': 'report.create', 'resource': 'report', 'action': 'create', 'description': 'Create reports'},
        {'name': 'report.read', 'resource': 'report', 'action': 'read', 'description': 'View reports'},
        {'name': 'audit.read', 'resource': 'audit', 'action': 'read', 'description': 'View audit logs'},
        {'name': 'api.access', 'resource': 'api', 'action': 'access', 'description': 'Access API endpoints'},
    ],
    UserRole.MANAGER: [
        # Management operations
        {'name': 'user.read', 'resource': 'user', 'action': 'read', 'description': 'View user information'},
        {'name': 'organization.read', 'resource': 'organization', 'action': 'read', 'description': 'View organization information'},
        {'name': 'farm.create', 'resource': 'farm', 'action': 'create', 'description': 'Create farm records'},
        {'name': 'farm.read', 'resource': 'farm', 'action': 'read', 'description': 'View farm information'},
        {'name': 'farm.update', 'resource': 'farm', 'action': 'update', 'description': 'Update farm information'},
        {'name': 'crop.create', 'resource': 'crop', 'action': 'create', 'description': 'Create crop records'},
        {'name': 'crop.read', 'resource': 'crop', 'action': 'read', 'description': 'View crop information'},
        {'name': 'crop.update', 'resource': 'crop', 'action': 'update', 'description': 'Update crop information'},
        {'name': 'inventory.read', 'resource': 'inventory', 'action': 'read', 'description': 'View inventory'},
        {'name': 'inventory.update', 'resource': 'inventory', 'action': 'update', 'description': 'Update inventory'},
        {'name': 'report.create', 'resource': 'report', 'action': 'create', 'description': 'Create reports'},
        {'name': 'report.read', 'resource': 'report', 'action': 'read', 'description': 'View reports'},
        {'name': 'api.access', 'resource': 'api', 'action': 'access', 'description': 'Access API endpoints'},
    ],
    UserRole.FIELD_OFFICER: [
        # Field operations
        {'name': 'farm.read', 'resource': 'farm', 'action': 'read', 'description': 'View farm information'},
        {'name': 'farm.update', 'resource': 'farm', 'action': 'update', 'description': 'Update farm information'},
        {'name': 'crop.create', 'resource': 'crop', 'action': 'create', 'description': 'Create crop records'},
        {'name': 'crop.read', 'resource': 'crop', 'action': 'read', 'description': 'View crop information'},
        {'name': 'crop.update', 'resource': 'crop', 'action': 'update', 'description': 'Update crop information'},
        {'name': 'field_data.create', 'resource': 'field_data', 'action': 'create', 'description': 'Create field data'},
        {'name': 'field_data.read', 'resource': 'field_data', 'action': 'read', 'description': 'View field data'},
        {'name': 'field_data.update', 'resource': 'field_data', 'action': 'update', 'description': 'Update field data'},
        {'name': 'inventory.read', 'resource': 'inventory', 'action': 'read', 'description': 'View inventory'},
        {'name': 'mobile.access', 'resource': 'mobile', 'action': 'access', 'description': 'Access mobile application'},
        {'name': 'api.access', 'resource': 'api', 'action': 'access', 'description': 'Access API endpoints'},
    ],
    UserRole.FARMER: [
        # Farmer operations
        {'name': 'farm.read', 'resource': 'farm', 'action': 'read', 'description': 'View own farm information'},
        {'name': 'crop.read', 'resource': 'crop', 'action': 'read', 'description': 'View own crop information'},
        {'name': 'field_data.read', 'resource': 'field_data', 'action': 'read', 'description': 'View own field data'},
        {'name': 'inventory.read', 'resource': 'inventory', 'action': 'read', 'description': 'View own inventory'},
        {'name': 'order.create', 'resource': 'order', 'action': 'create', 'description': 'Create orders'},
        {'name': 'order.read', 'resource': 'order', 'action': 'read', 'description': 'View own orders'},
        {'name': 'mobile.access', 'resource': 'mobile', 'action': 'access', 'description': 'Access mobile application'},
        {'name': 'notification.read', 'resource': 'notification', 'action': 'read', 'description': 'View notifications'},
    ],
    UserRole.INPUT_SUPPLIER: [
        # Input supplier operations
        {'name': 'product.create', 'resource': 'product', 'action': 'create', 'description': 'Create product listings'},
        {'name': 'product.read', 'resource': 'product', 'action': 'read', 'description': 'View product information'},
        {'name': 'product.update', 'resource': 'product', 'action': 'update', 'description': 'Update product information'},
        {'name': 'inventory.read', 'resource': 'inventory', 'action': 'read', 'description': 'View own inventory'},
        {'name': 'inventory.update', 'resource': 'inventory', 'action': 'update', 'description': 'Update own inventory'},
        {'name': 'order.read', 'resource': 'order', 'action': 'read', 'description': 'View orders'},
        {'name': 'order.update', 'resource': 'order', 'action': 'update', 'description': 'Update order status'},
        {'name': 'partner_api.access', 'resource': 'partner_api', 'action': 'access', 'description': 'Access partner API'},
        {'name': 'report.read', 'resource': 'report', 'action': 'read', 'description': 'View sales reports'},
    ],
    UserRole.LOGISTICS_PARTNER: [
        # Logistics operations
        {'name': 'shipment.create', 'resource': 'shipment', 'action': 'create', 'description': 'Create shipments'},
        {'name': 'shipment.read', 'resource': 'shipment', 'action': 'read', 'description': 'View shipment information'},
        {'name': 'shipment.update', 'resource': 'shipment', 'action': 'update', 'description': 'Update shipment status'},
        {'name': 'delivery.create', 'resource': 'delivery', 'action': 'create', 'description': 'Create delivery records'},
        {'name': 'delivery.read', 'resource': 'delivery', 'action': 'read', 'description': 'View delivery information'},
        {'name': 'delivery.update', 'resource': 'delivery', 'action': 'update', 'description': 'Update delivery status'},
        {'name': 'tracking.read', 'resource': 'tracking', 'action': 'read', 'description': 'View tracking information'},
        {'name': 'partner_api.access', 'resource': 'partner_api', 'action': 'access', 'description': 'Access partner API'},
        {'name': 'mobile.access', 'resource': 'mobile', 'action': 'access', 'description': 'Access mobile application'},
    ],
    UserRole.FINANCIAL_PARTNER: [
        # Financial operations
        {'name': 'payment.create', 'resource': 'payment', 'action': 'create', 'description': 'Process payments'},
        {'name': 'payment.read', 'resource': 'payment', 'action': 'read', 'description': 'View payment information'},
        {'name': 'payment.update', 'resource': 'payment', 'action': 'update', 'description': 'Update payment status'},
        {'name': 'loan.create', 'resource': 'loan', 'action': 'create', 'description': 'Create loan records'},
        {'name': 'loan.read', 'resource': 'loan', 'action': 'read', 'description': 'View loan information'},
        {'name': 'loan.update', 'resource': 'loan', 'action': 'update', 'description': 'Update loan status'},
        {'name': 'credit.read', 'resource': 'credit', 'action': 'read', 'description': 'View credit information'},
        {'name': 'financial_report.read', 'resource': 'financial_report', 'action': 'read', 'description': 'View financial reports'},
        {'name': 'partner_api.access', 'resource': 'partner_api', 'action': 'access', 'description': 'Access partner API'},
    ],
    UserRole.BUYER_PROCESSOR: [
        # Buyer/processor operations
        {'name': 'purchase.create', 'resource': 'purchase', 'action': 'create', 'description': 'Create purchase orders'},
        {'name': 'purchase.read', 'resource': 'purchase', 'action': 'read', 'description': 'View purchase information'},
        {'name': 'purchase.update', 'resource': 'purchase', 'action': 'update', 'description': 'Update purchase status'},
        {'name': 'quality.read', 'resource': 'quality', 'action': 'read', 'description': 'View quality assessments'},
        {'name': 'quality.create', 'resource': 'quality', 'action': 'create', 'description': 'Create quality assessments'},
        {'name': 'pricing.read', 'resource': 'pricing', 'action': 'read', 'description': 'View pricing information'},
        {'name': 'contract.create', 'resource': 'contract', 'action': 'create', 'description': 'Create contracts'},
        {'name': 'contract.read', 'resource': 'contract', 'action': 'read', 'description': 'View contracts'},
        {'name': 'partner_api.access', 'resource': 'partner_api', 'action': 'access', 'description': 'Access partner API'},
        {'name': 'report.read', 'resource': 'report', 'action': 'read', 'description': 'View purchase reports'},
    ]
}

@permission_bp.route('/permissions', methods=['GET'])
@jwt_required()
def get_permissions():
    """Get all permissions or permissions for a specific role"""
    try:
        role_param = request.args.get('role')
        
        if role_param:
            try:
                role = UserRole(role_param)
                permissions = Permission.query.filter_by(role=role).all()
            except ValueError:
                return jsonify({'error': 'Invalid role'}), 400
        else:
            permissions = Permission.query.all()
        
        return jsonify({
            'permissions': [perm.to_dict() for perm in permissions]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get permissions error: {str(e)}")
        return jsonify({'error': 'Failed to get permissions'}), 500

@permission_bp.route('/permissions/initialize', methods=['POST'])
@require_permission('permission.manage')
def initialize_permissions():
    """Initialize default permissions for all roles"""
    try:
        current_user_id = get_jwt_identity()
        
        # Clear existing permissions
        Permission.query.delete()
        
        # Add default permissions for each role
        for role, permissions in DEFAULT_PERMISSIONS.items():
            for perm_data in permissions:
                permission = Permission(
                    name=perm_data['name'],
                    description=perm_data['description'],
                    resource=perm_data['resource'],
                    action=perm_data['action'],
                    role=role
                )
                db.session.add(permission)
        
        db.session.commit()
        
        log_audit_event(
            action='PERMISSIONS_INITIALIZED',
            resource='permission',
            details={'total_permissions': sum(len(perms) for perms in DEFAULT_PERMISSIONS.values())},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Permissions initialized successfully',
            'total_permissions': sum(len(perms) for perms in DEFAULT_PERMISSIONS.values())
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Initialize permissions error: {str(e)}")
        return jsonify({'error': 'Failed to initialize permissions'}), 500

@permission_bp.route('/permissions', methods=['POST'])
@require_permission('permission.manage')
def create_permission():
    """Create a new permission"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'resource', 'action', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate role
        try:
            role = UserRole(data['role'])
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Check if permission already exists
        existing_permission = Permission.query.filter_by(
            name=data['name'],
            role=role
        ).first()
        
        if existing_permission:
            return jsonify({'error': 'Permission already exists for this role'}), 409
        
        # Create new permission
        permission = Permission(
            name=data['name'],
            description=data.get('description'),
            resource=data['resource'],
            action=data['action'],
            role=role
        )
        
        db.session.add(permission)
        db.session.commit()
        
        log_audit_event(
            action='PERMISSION_CREATED',
            resource='permission',
            resource_id=permission.id,
            details=permission.to_dict(),
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Permission created successfully',
            'permission': permission.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create permission error: {str(e)}")
        return jsonify({'error': 'Failed to create permission'}), 500

@permission_bp.route('/permissions/<int:permission_id>', methods=['PUT'])
@require_permission('permission.manage')
def update_permission(permission_id):
    """Update a permission"""
    try:
        current_user_id = get_jwt_identity()
        permission = Permission.query.get(permission_id)
        
        if not permission:
            return jsonify({'error': 'Permission not found'}), 404
        
        data = request.get_json()
        old_data = permission.to_dict()
        
        # Update fields
        if 'name' in data:
            permission.name = data['name']
        if 'description' in data:
            permission.description = data['description']
        if 'resource' in data:
            permission.resource = data['resource']
        if 'action' in data:
            permission.action = data['action']
        if 'role' in data:
            try:
                permission.role = UserRole(data['role'])
            except ValueError:
                return jsonify({'error': 'Invalid role'}), 400
        
        db.session.commit()
        
        log_audit_event(
            action='PERMISSION_UPDATED',
            resource='permission',
            resource_id=permission.id,
            details={'old_data': old_data, 'new_data': permission.to_dict()},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Permission updated successfully',
            'permission': permission.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update permission error: {str(e)}")
        return jsonify({'error': 'Failed to update permission'}), 500

@permission_bp.route('/permissions/<int:permission_id>', methods=['DELETE'])
@require_permission('permission.manage')
def delete_permission(permission_id):
    """Delete a permission"""
    try:
        current_user_id = get_jwt_identity()
        permission = Permission.query.get(permission_id)
        
        if not permission:
            return jsonify({'error': 'Permission not found'}), 404
        
        permission_data = permission.to_dict()
        db.session.delete(permission)
        db.session.commit()
        
        log_audit_event(
            action='PERMISSION_DELETED',
            resource='permission',
            resource_id=permission_id,
            details=permission_data,
            user_id=current_user_id
        )
        
        return jsonify({'message': 'Permission deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete permission error: {str(e)}")
        return jsonify({'error': 'Failed to delete permission'}), 500

@permission_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_roles():
    """Get all available roles and their descriptions"""
    try:
        roles = []
        for role in UserRole:
            role_permissions = Permission.query.filter_by(role=role).all()
            roles.append({
                'value': role.value,
                'name': role.name,
                'description': get_role_description(role),
                'permission_count': len(role_permissions),
                'permissions': [perm.to_dict() for perm in role_permissions]
            })
        
        return jsonify({'roles': roles}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get roles error: {str(e)}")
        return jsonify({'error': 'Failed to get roles'}), 500

@permission_bp.route('/permissions/check', methods=['POST'])
@jwt_required()
def check_permission():
    """Check if current user has a specific permission"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        permission_name = data.get('permission')
        organization_id = data.get('organization_id')
        
        if not permission_name:
            return jsonify({'error': 'Permission name required'}), 400
        
        has_permission = user.has_permission(permission_name, organization_id)
        
        return jsonify({
            'has_permission': has_permission,
            'permission': permission_name,
            'organization_id': organization_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Check permission error: {str(e)}")
        return jsonify({'error': 'Failed to check permission'}), 500

def get_role_description(role):
    """Get human-readable description for a role"""
    descriptions = {
        UserRole.SUPER_ADMIN: "System administrator with full access to all features and organizations",
        UserRole.ADMIN: "Organization administrator with full access within their organization",
        UserRole.MANAGER: "Management role with access to operational features and reporting",
        UserRole.FIELD_OFFICER: "Field operations role with access to farm and crop management",
        UserRole.FARMER: "Farmer role with access to their own farm data and basic features",
        UserRole.INPUT_SUPPLIER: "Partner role for input suppliers with product and inventory management",
        UserRole.LOGISTICS_PARTNER: "Partner role for logistics companies with shipment and delivery management",
        UserRole.FINANCIAL_PARTNER: "Partner role for financial institutions with payment and loan management",
        UserRole.BUYER_PROCESSOR: "Partner role for buyers and processors with purchase and quality management"
    }
    return descriptions.get(role, "No description available")
