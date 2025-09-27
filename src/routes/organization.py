from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from src.models.user import (
    db, User, Organization, UserRole, UserStatus, 
    user_organizations, AuditLog
)
from src.routes.auth import require_permission, log_audit_event

organization_bp = Blueprint('organization', __name__)

@organization_bp.route('/organizations', methods=['GET'])
@jwt_required()
def get_organizations():
    """Get all organizations (admin only) or user's organizations"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is super admin or admin
        is_admin = any(
            user.get_role_in_organization(org.id) in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            for org in user.organizations
        )
        
        if is_admin:
            # Admin can see all organizations
            organizations = Organization.query.all()
        else:
            # Regular users can only see their organizations
            organizations = user.organizations
        
        return jsonify({
            'organizations': [org.to_dict() for org in organizations]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get organizations error: {str(e)}")
        return jsonify({'error': 'Failed to get organizations'}), 500

@organization_bp.route('/organizations', methods=['POST'])
@require_permission('organization.create')
def create_organization():
    """Create a new organization"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'code', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if organization code already exists
        if Organization.query.filter_by(code=data['code']).first():
            return jsonify({'error': 'Organization code already exists'}), 409
        
        # Validate organization type
        valid_types = ['internal', 'partner', 'client']
        if data['type'] not in valid_types:
            return jsonify({'error': f'Invalid organization type. Must be one of: {valid_types}'}), 400
        
        # Create new organization
        organization = Organization(
            name=data['name'],
            code=data['code'],
            type=data['type'],
            description=data.get('description'),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone'),
            address=data.get('address'),
            status=UserStatus.ACTIVE
        )
        
        db.session.add(organization)
        db.session.commit()
        
        log_audit_event(
            action='ORGANIZATION_CREATED',
            resource='organization',
            resource_id=organization.id,
            details=organization.to_dict(),
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Organization created successfully',
            'organization': organization.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create organization error: {str(e)}")
        return jsonify({'error': 'Failed to create organization'}), 500

@organization_bp.route('/organizations/<int:org_id>', methods=['GET'])
@jwt_required()
def get_organization(org_id):
    """Get organization details"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        organization = Organization.query.get(org_id)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Check if user has access to this organization
        user_role = user.get_role_in_organization(org_id)
        is_admin = any(
            user.get_role_in_organization(org.id) in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            for org in user.organizations
        )
        
        if not user_role and not is_admin:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get organization users if user has permission
        org_data = organization.to_dict()
        if user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER] or is_admin:
            # Get users in this organization
            users_in_org = []
            for org_user in organization.users:
                user_role_in_org = org_user.get_role_in_organization(org_id)
                users_in_org.append({
                    'user': org_user.to_dict(),
                    'role': user_role_in_org.value if user_role_in_org else None
                })
            org_data['users'] = users_in_org
        
        return jsonify({'organization': org_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get organization error: {str(e)}")
        return jsonify({'error': 'Failed to get organization'}), 500

@organization_bp.route('/organizations/<int:org_id>', methods=['PUT'])
@require_permission('organization.update')
def update_organization(org_id):
    """Update organization details"""
    try:
        current_user_id = get_jwt_identity()
        organization = Organization.query.get(org_id)
        
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        data = request.get_json()
        old_data = organization.to_dict()
        
        # Update fields
        if 'name' in data:
            organization.name = data['name']
        if 'description' in data:
            organization.description = data['description']
        if 'contact_email' in data:
            organization.contact_email = data['contact_email']
        if 'contact_phone' in data:
            organization.contact_phone = data['contact_phone']
        if 'address' in data:
            organization.address = data['address']
        if 'status' in data:
            try:
                organization.status = UserStatus(data['status'])
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        organization.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        log_audit_event(
            action='ORGANIZATION_UPDATED',
            resource='organization',
            resource_id=organization.id,
            details={'old_data': old_data, 'new_data': organization.to_dict()},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Organization updated successfully',
            'organization': organization.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update organization error: {str(e)}")
        return jsonify({'error': 'Failed to update organization'}), 500

@organization_bp.route('/organizations/<int:org_id>/users', methods=['POST'])
@require_permission('organization.manage_users')
def add_user_to_organization(org_id):
    """Add a user to an organization with a specific role"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if 'user_id' not in data or 'role' not in data:
            return jsonify({'error': 'User ID and role are required'}), 400
        
        organization = Organization.query.get(org_id)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Validate role
        try:
            role = UserRole(data['role'])
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Check if user is already in organization
        existing_role = user.get_role_in_organization(org_id)
        if existing_role:
            return jsonify({'error': 'User is already in this organization'}), 409
        
        # Add user to organization
        is_primary = data.get('is_primary', False)
        association = user_organizations.insert().values(
            user_id=data['user_id'],
            organization_id=org_id,
            role=role,
            is_primary=is_primary
        )
        db.session.execute(association)
        db.session.commit()
        
        log_audit_event(
            action='USER_ADDED_TO_ORGANIZATION',
            resource='organization',
            resource_id=org_id,
            details={
                'user_id': data['user_id'],
                'role': role.value,
                'is_primary': is_primary
            },
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'User added to organization successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add user to organization error: {str(e)}")
        return jsonify({'error': 'Failed to add user to organization'}), 500

@organization_bp.route('/organizations/<int:org_id>/users/<int:user_id>', methods=['PUT'])
@require_permission('organization.manage_users')
def update_user_role_in_organization(org_id, user_id):
    """Update a user's role in an organization"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if 'role' not in data:
            return jsonify({'error': 'Role is required'}), 400
        
        organization = Organization.query.get(org_id)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Validate role
        try:
            new_role = UserRole(data['role'])
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Check if user is in organization
        old_role = user.get_role_in_organization(org_id)
        if not old_role:
            return jsonify({'error': 'User is not in this organization'}), 404
        
        # Update user role
        association = db.session.query(user_organizations).filter_by(
            user_id=user_id,
            organization_id=org_id
        ).first()
        
        if association:
            db.session.execute(
                user_organizations.update().where(
                    (user_organizations.c.user_id == user_id) &
                    (user_organizations.c.organization_id == org_id)
                ).values(role=new_role)
            )
            db.session.commit()
            
            log_audit_event(
                action='USER_ROLE_UPDATED',
                resource='organization',
                resource_id=org_id,
                details={
                    'user_id': user_id,
                    'old_role': old_role.value,
                    'new_role': new_role.value
                },
                user_id=current_user_id
            )
            
            return jsonify({
                'message': 'User role updated successfully'
            }), 200
        else:
            return jsonify({'error': 'User association not found'}), 404
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update user role error: {str(e)}")
        return jsonify({'error': 'Failed to update user role'}), 500

@organization_bp.route('/organizations/<int:org_id>/users/<int:user_id>', methods=['DELETE'])
@require_permission('organization.manage_users')
def remove_user_from_organization(org_id, user_id):
    """Remove a user from an organization"""
    try:
        current_user_id = get_jwt_identity()
        
        organization = Organization.query.get(org_id)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is in organization
        user_role = user.get_role_in_organization(org_id)
        if not user_role:
            return jsonify({'error': 'User is not in this organization'}), 404
        
        # Remove user from organization
        db.session.execute(
            user_organizations.delete().where(
                (user_organizations.c.user_id == user_id) &
                (user_organizations.c.organization_id == org_id)
            )
        )
        db.session.commit()
        
        log_audit_event(
            action='USER_REMOVED_FROM_ORGANIZATION',
            resource='organization',
            resource_id=org_id,
            details={
                'user_id': user_id,
                'role': user_role.value
            },
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'User removed from organization successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Remove user from organization error: {str(e)}")
        return jsonify({'error': 'Failed to remove user from organization'}), 500

@organization_bp.route('/organizations/<int:org_id>/stats', methods=['GET'])
@jwt_required()
def get_organization_stats(org_id):
    """Get organization statistics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        organization = Organization.query.get(org_id)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Check if user has access to this organization
        user_role = user.get_role_in_organization(org_id)
        is_admin = any(
            user.get_role_in_organization(org.id) in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            for org in user.organizations
        )
        
        if not user_role and not is_admin:
            return jsonify({'error': 'Access denied'}), 403
        
        # Calculate statistics
        total_users = len(organization.users)
        
        # Count users by role
        role_counts = {}
        for org_user in organization.users:
            user_role_in_org = org_user.get_role_in_organization(org_id)
            if user_role_in_org:
                role_name = user_role_in_org.value
                role_counts[role_name] = role_counts.get(role_name, 0) + 1
        
        # Count users by status
        status_counts = {}
        for org_user in organization.users:
            status_name = org_user.status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        # Get recent audit logs for this organization
        recent_logs = AuditLog.query.filter_by(
            organization_id=org_id
        ).order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        return jsonify({
            'organization_id': org_id,
            'total_users': total_users,
            'role_distribution': role_counts,
            'status_distribution': status_counts,
            'recent_activity': [log.to_dict() for log in recent_logs]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get organization stats error: {str(e)}")
        return jsonify({'error': 'Failed to get organization statistics'}), 500
