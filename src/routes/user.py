from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from src.models.user import User, db, UserRole, UserStatus, Organization, user_organizations
from src.routes.auth import require_permission, log_audit_event, validate_password_strength

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users (with proper access control)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has permission to view users
        if not current_user.has_permission('user.read'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Get query parameters
        organization_id = request.args.get('organization_id', type=int)
        role = request.args.get('role')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = User.query
        
        # Filter by organization if specified
        if organization_id:
            query = query.join(User.organizations).filter(Organization.id == organization_id)
        
        # Filter by status if specified
        if status:
            try:
                status_enum = UserStatus(status)
                query = query.filter(User.status == status_enum)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        # Paginate results
        users_pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        users_data = []
        for user in users_pagination.items:
            user_data = user.to_dict(include_organizations=True)
            
            # Filter role if specified
            if role:
                user_orgs = user_data.get('organizations', [])
                filtered_orgs = [org for org in user_orgs if org.get('role') == role]
                if not filtered_orgs:
                    continue
                user_data['organizations'] = filtered_orgs
            
            users_data.append(user_data)
        
        return jsonify({
            'users': users_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': users_pagination.total,
                'pages': users_pagination.pages,
                'has_next': users_pagination.has_next,
                'has_prev': users_pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get users error: {str(e)}")
        return jsonify({'error': 'Failed to get users'}), 500

@user_bp.route('/users', methods=['POST'])
@require_permission('user.create')
def create_user():
    """Create a new user (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'organization_id', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Validate password strength
        is_valid, message = validate_password_strength(data['password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Validate role
        try:
            role = UserRole(data['role'])
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Validate organization exists
        organization = Organization.query.get(data['organization_id'])
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            status=UserStatus.ACTIVE,  # Admin-created users are active by default
            email_verified=True  # Admin-created users are verified by default
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Add user to organization with specified role
        association = user_organizations.insert().values(
            user_id=user.id,
            organization_id=data['organization_id'],
            role=role,
            is_primary=True
        )
        db.session.execute(association)
        db.session.commit()
        
        log_audit_event(
            action='USER_CREATED',
            resource='user',
            resource_id=user.id,
            details={'organization_id': data['organization_id'], 'role': role.value},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict(include_organizations=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create user error: {str(e)}")
        return jsonify({'error': 'Failed to create user'}), 500

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get user by ID"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check permissions - users can view their own profile or admins can view any user
        if user_id != current_user_id and not current_user.has_permission('user.read'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        return jsonify({'user': user.to_dict(include_organizations=True)}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Failed to get user'}), 500

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user information"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check permissions - users can update their own profile or admins can update any user
        if user_id != current_user_id and not current_user.has_permission('user.update'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        old_data = user.to_dict()
        
        # Update basic fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        
        # Only admins can update these fields
        if current_user.has_permission('user.update'):
            if 'email' in data:
                # Check if email is already taken by another user
                existing_user = User.query.filter_by(email=data['email']).first()
                if existing_user and existing_user.id != user_id:
                    return jsonify({'error': 'Email already exists'}), 409
                user.email = data['email']
                user.email_verified = False  # Require re-verification
            
            if 'username' in data:
                # Check if username is already taken by another user
                existing_user = User.query.filter_by(username=data['username']).first()
                if existing_user and existing_user.id != user_id:
                    return jsonify({'error': 'Username already exists'}), 409
                user.username = data['username']
            
            if 'status' in data:
                try:
                    user.status = UserStatus(data['status'])
                except ValueError:
                    return jsonify({'error': 'Invalid status'}), 400
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        log_audit_event(
            action='USER_UPDATED',
            resource='user',
            resource_id=user.id,
            details={'old_data': old_data, 'new_data': user.to_dict()},
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict(include_organizations=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update user error: {str(e)}")
        return jsonify({'error': 'Failed to update user'}), 500

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_permission('user.delete')
def delete_user(user_id):
    """Delete a user"""
    try:
        current_user_id = get_jwt_identity()
        
        # Prevent self-deletion
        if user_id == current_user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user.to_dict()
        
        # Remove user from all organizations
        db.session.execute(
            user_organizations.delete().where(user_organizations.c.user_id == user_id)
        )
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        log_audit_event(
            action='USER_DELETED',
            resource='user',
            resource_id=user_id,
            details=user_data,
            user_id=current_user_id
        )
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete user error: {str(e)}")
        return jsonify({'error': 'Failed to delete user'}), 500

@user_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@require_permission('user.update')
def reset_user_password(user_id):
    """Reset a user's password (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Update password
        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        log_audit_event(
            action='PASSWORD_RESET',
            resource='user',
            resource_id=user.id,
            details={'reset_by_admin': True},
            user_id=current_user_id
        )
        
        return jsonify({'message': 'Password reset successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({'error': 'Failed to reset password'}), 500

@user_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@require_permission('user.update')
def unlock_user_account(user_id):
    """Unlock a user's account (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Unlock account
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        log_audit_event(
            action='ACCOUNT_UNLOCKED',
            resource='user',
            resource_id=user.id,
            user_id=current_user_id
        )
        
        return jsonify({'message': 'Account unlocked successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unlock account error: {str(e)}")
        return jsonify({'error': 'Failed to unlock account'}), 500

@user_bp.route('/users/stats', methods=['GET'])
@require_permission('user.read')
def get_user_stats():
    """Get user statistics"""
    try:
        # Count users by status
        status_counts = {}
        for status in UserStatus:
            count = User.query.filter_by(status=status).count()
            status_counts[status.value] = count
        
        # Count users by role
        role_counts = {}
        for role in UserRole:
            # Count users with this role across all organizations
            count = db.session.query(user_organizations).filter_by(role=role).count()
            role_counts[role.value] = count
        
        # Total users
        total_users = User.query.count()
        
        # Recent registrations (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_registrations = User.query.filter(User.created_at >= thirty_days_ago).count()
        
        return jsonify({
            'total_users': total_users,
            'status_distribution': status_counts,
            'role_distribution': role_counts,
            'recent_registrations': recent_registrations
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get user stats error: {str(e)}")
        return jsonify({'error': 'Failed to get user statistics'}), 500
