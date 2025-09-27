from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from datetime import datetime, timedelta, timezone
import secrets
import re
from functools import wraps

from src.models.user import (
    db, User, UserSession, AuditLog, Organization, 
    UserRole, UserStatus, user_organizations
)

auth_bp = Blueprint('auth', __name__)

def log_audit_event(action, resource, resource_id=None, details=None, user_id=None):
    """Helper function to log audit events"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
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
        current_app.logger.error(f"Failed to log audit event: {str(e)}")

def validate_password_strength(password):
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def require_permission(permission, organization_required=False):
    """Decorator to check if user has required permission"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user or user.status != UserStatus.ACTIVE:
                return jsonify({'error': 'User not found or inactive'}), 401
            
            organization_id = request.json.get('organization_id') if request.json else None
            if organization_required and not organization_id:
                return jsonify({'error': 'Organization ID required'}), 400
            
            if not user.has_permission(permission, organization_id):
                log_audit_event(
                    action='PERMISSION_DENIED',
                    resource=permission,
                    details={'required_permission': permission, 'organization_id': organization_id},
                    user_id=current_user_id
                )
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
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
            status=UserStatus.PENDING,
            email_verification_token=secrets.token_urlsafe(32)
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
            action='USER_REGISTERED',
            resource='user',
            resource_id=user.id,
            details={'organization_id': data['organization_id'], 'role': role.value}
        )
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'verification_required': True
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password required'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user:
            log_audit_event(
                action='LOGIN_FAILED',
                resource='user',
                details={'reason': 'user_not_found', 'username': data['username']}
            )
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if account is locked
        if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
            log_audit_event(
                action='LOGIN_FAILED',
                resource='user',
                resource_id=user.id,
                details={'reason': 'account_locked'},
                user_id=user.id
            )
            return jsonify({'error': 'Account is locked. Please try again later.'}), 423
        
        # Check password
        if not user.check_password(data['password']):
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            db.session.commit()
            
            log_audit_event(
                action='LOGIN_FAILED',
                resource='user',
                resource_id=user.id,
                details={'reason': 'invalid_password', 'failed_attempts': user.failed_login_attempts},
                user_id=user.id
            )
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check user status
        if user.status != UserStatus.ACTIVE:
            log_audit_event(
                action='LOGIN_FAILED',
                resource='user',
                resource_id=user.id,
                details={'reason': 'user_inactive', 'status': user.status.value},
                user_id=user.id
            )
            return jsonify({'error': 'Account is not active'}), 401
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.now(timezone.utc)
        
        # Create JWT tokens
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            session_token=secrets.token_urlsafe(32),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        db.session.add(session)
        db.session.commit()
        
        log_audit_event(
            action='LOGIN_SUCCESS',
            resource='user',
            resource_id=user.id,
            details={'session_id': session.id},
            user_id=user.id
        )
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(include_organizations=True),
            'session_id': session.id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.status != UserStatus.ACTIVE:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        new_access_token = create_access_token(
            identity=current_user_id,
            expires_delta=timedelta(hours=1)
        )
        
        log_audit_event(
            action='TOKEN_REFRESHED',
            resource='user',
            resource_id=current_user_id,
            user_id=current_user_id
        )
        
        return jsonify({'access_token': new_access_token}), 200
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Token refresh failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user and invalidate session"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        session_id = data.get('session_id') if data else None
        
        if session_id:
            session = UserSession.query.filter_by(
                id=session_id, 
                user_id=current_user_id
            ).first()
            if session:
                session.is_active = False
                db.session.commit()
        
        log_audit_event(
            action='LOGOUT',
            resource='user',
            resource_id=current_user_id,
            details={'session_id': session_id},
            user_id=current_user_id
        )
        
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user's profile"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict(include_organizations=True)}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user's password"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password required'}), 400
        
        # Verify current password
        if not user.check_password(data['current_password']):
            log_audit_event(
                action='PASSWORD_CHANGE_FAILED',
                resource='user',
                resource_id=current_user_id,
                details={'reason': 'invalid_current_password'},
                user_id=current_user_id
            )
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password strength
        is_valid, message = validate_password_strength(data['new_password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Update password
        user.set_password(data['new_password'])
        db.session.commit()
        
        log_audit_event(
            action='PASSWORD_CHANGED',
            resource='user',
            resource_id=current_user_id,
            user_id=current_user_id
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify user's email address"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Verification token required'}), 400
        
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            return jsonify({'error': 'Invalid verification token'}), 400
        
        user.email_verified = True
        user.email_verification_token = None
        user.status = UserStatus.ACTIVE
        db.session.commit()
        
        log_audit_event(
            action='EMAIL_VERIFIED',
            resource='user',
            resource_id=user.id,
            user_id=user.id
        )
        
        return jsonify({'message': 'Email verified successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Email verification error: {str(e)}")
        return jsonify({'error': 'Email verification failed'}), 500

@auth_bp.route('/permissions', methods=['GET'])
@jwt_required()
def get_user_permissions():
    """Get current user's permissions"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        permissions = {}
        for org in user.organizations:
            role = user.get_role_in_organization(org.id)
            if role:
                from src.models.user import Permission
                org_permissions = Permission.query.filter_by(role=role).all()
                permissions[org.id] = {
                    'organization': org.to_dict(),
                    'role': role.value,
                    'permissions': [perm.to_dict() for perm in org_permissions]
                }
        
        return jsonify({'permissions': permissions}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get permissions error: {str(e)}")
        return jsonify({'error': 'Failed to get permissions'}), 500
