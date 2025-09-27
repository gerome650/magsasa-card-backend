"""
Organization analytics and multi-tenant management routes
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_, or_

from src.models.user import (
    db, User, Organization, UserRole, UserStatus, 
    AuditLog, UserSession, user_organizations
)
from src.routes.auth import require_permission, log_audit_event
from src.middleware.tenant import (
    tenant_required, TenantContext, get_tenant_stats,
    validate_cross_tenant_access
)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/dashboard', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
def get_dashboard_analytics():
    """Get comprehensive dashboard analytics for current organization"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        organization = TenantContext.get_organization()
        
        if not organization_id:
            return jsonify({'error': 'Organization context required'}), 400
        
        # Get basic tenant stats
        tenant_stats = get_tenant_stats()
        
        # Calculate time-based metrics
        now = datetime.now(timezone.utc)
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        last_24_hours = now - timedelta(hours=24)
        
        # User activity metrics
        total_users = len(organization.users)
        active_users_30d = User.query.join(User.organizations).filter(
            Organization.id == organization_id,
            User.last_login >= last_30_days
        ).count()
        
        active_users_7d = User.query.join(User.organizations).filter(
            Organization.id == organization_id,
            User.last_login >= last_7_days
        ).count()
        
        # Authentication metrics
        login_attempts_24h = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action.in_(['LOGIN_SUCCESS', 'LOGIN_FAILED']),
            AuditLog.timestamp >= last_24_hours
        ).count()
        
        successful_logins_24h = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == 'LOGIN_SUCCESS',
            AuditLog.timestamp >= last_24_hours
        ).count()
        
        failed_logins_24h = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == 'LOGIN_FAILED',
            AuditLog.timestamp >= last_24_hours
        ).count()
        
        # Security metrics
        locked_accounts = User.query.join(User.organizations).filter(
            Organization.id == organization_id,
            User.account_locked_until > now
        ).count()
        
        pending_users = User.query.join(User.organizations).filter(
            Organization.id == organization_id,
            User.status == UserStatus.PENDING
        ).count()
        
        # Activity trends (last 7 days)
        activity_trend = []
        for i in range(7):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            daily_activity = AuditLog.query.filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= day_start,
                AuditLog.timestamp < day_end
            ).count()
            
            activity_trend.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'activity_count': daily_activity
            })
        
        activity_trend.reverse()  # Show oldest to newest
        
        # Top active users (last 30 days)
        top_users = db.session.query(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            func.count(AuditLog.id).label('activity_count')
        ).join(AuditLog, User.id == AuditLog.user_id).join(
            User.organizations
        ).filter(
            Organization.id == organization_id,
            AuditLog.timestamp >= last_30_days
        ).group_by(User.id).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()
        
        top_users_data = [
            {
                'user_id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}",
                'activity_count': user.activity_count
            }
            for user in top_users
        ]
        
        # Permission usage analytics
        permission_usage = db.session.query(
            AuditLog.action,
            func.count(AuditLog.id).label('usage_count')
        ).filter(
            AuditLog.organization_id == organization_id,
            AuditLog.timestamp >= last_30_days
        ).group_by(AuditLog.action).order_by(
            func.count(AuditLog.id).desc()
        ).limit(15).all()
        
        permission_usage_data = [
            {
                'action': perm.action,
                'usage_count': perm.usage_count
            }
            for perm in permission_usage
        ]
        
        # Compile dashboard data
        dashboard_data = {
            'organization': {
                'id': organization.id,
                'name': organization.name,
                'type': organization.type,
                'created_at': organization.created_at.isoformat() if organization.created_at else None
            },
            'user_metrics': {
                'total_users': total_users,
                'active_users_30d': active_users_30d,
                'active_users_7d': active_users_7d,
                'pending_users': pending_users,
                'locked_accounts': locked_accounts,
                'role_distribution': tenant_stats.get('role_distribution', {})
            },
            'authentication_metrics': {
                'login_attempts_24h': login_attempts_24h,
                'successful_logins_24h': successful_logins_24h,
                'failed_logins_24h': failed_logins_24h,
                'success_rate': (successful_logins_24h / login_attempts_24h * 100) if login_attempts_24h > 0 else 0
            },
            'activity_trends': {
                'daily_activity_7d': activity_trend,
                'total_activity_30d': tenant_stats.get('recent_activity_count', 0)
            },
            'top_users': top_users_data,
            'permission_usage': permission_usage_data,
            'generated_at': now.isoformat()
        }
        
        log_audit_event(
            action='ANALYTICS_VIEWED',
            resource='analytics',
            details={'type': 'dashboard'},
            user_id=current_user_id
        )
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Dashboard analytics error: {str(e)}")
        return jsonify({'error': 'Failed to generate dashboard analytics'}), 500

@analytics_bp.route('/analytics/users', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
def get_user_analytics():
    """Get detailed user analytics for current organization"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        organization = TenantContext.get_organization()
        
        if not organization_id:
            return jsonify({'error': 'Organization context required'}), 400
        
        # Time filters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # User registration trends
        registration_trend = []
        for i in range(days):
            day_start = (end_date - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            daily_registrations = User.query.join(User.organizations).filter(
                Organization.id == organization_id,
                User.created_at >= day_start,
                User.created_at < day_end
            ).count()
            
            registration_trend.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'registrations': daily_registrations
            })
        
        registration_trend.reverse()
        
        # User status breakdown
        status_breakdown = {}
        for status in UserStatus:
            count = User.query.join(User.organizations).filter(
                Organization.id == organization_id,
                User.status == status
            ).count()
            status_breakdown[status.value] = count
        
        # Role distribution with details
        role_details = {}
        for role in UserRole:
            users_with_role = db.session.query(user_organizations).filter(
                user_organizations.c.organization_id == organization_id,
                user_organizations.c.role == role
            ).count()
            
            if users_with_role > 0:
                role_details[role.value] = {
                    'count': users_with_role,
                    'percentage': (users_with_role / len(organization.users) * 100) if len(organization.users) > 0 else 0
                }
        
        # Login frequency analysis
        login_frequency = db.session.query(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            func.count(AuditLog.id).label('login_count'),
            func.max(AuditLog.timestamp).label('last_login')
        ).join(AuditLog, User.id == AuditLog.user_id).join(
            User.organizations
        ).filter(
            Organization.id == organization_id,
            AuditLog.action == 'LOGIN_SUCCESS',
            AuditLog.timestamp >= start_date
        ).group_by(User.id).order_by(
            func.count(AuditLog.id).desc()
        ).all()
        
        login_frequency_data = [
            {
                'user_id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}",
                'login_count': user.login_count,
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
            for user in login_frequency
        ]
        
        # Inactive users (no login in specified period)
        inactive_users = User.query.join(User.organizations).filter(
            Organization.id == organization_id,
            or_(
                User.last_login < start_date,
                User.last_login.is_(None)
            ),
            User.status == UserStatus.ACTIVE
        ).all()
        
        inactive_users_data = [
            {
                'user_id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}",
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
            for user in inactive_users
        ]
        
        user_analytics = {
            'organization_id': organization_id,
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'registration_trends': registration_trend,
            'status_breakdown': status_breakdown,
            'role_distribution': role_details,
            'login_frequency': login_frequency_data,
            'inactive_users': inactive_users_data,
            'summary': {
                'total_users': len(organization.users),
                'active_users': status_breakdown.get('active', 0),
                'inactive_user_count': len(inactive_users_data),
                'most_active_role': max(role_details.items(), key=lambda x: x[1]['count'])[0] if role_details else None
            }
        }
        
        log_audit_event(
            action='ANALYTICS_VIEWED',
            resource='analytics',
            details={'type': 'users', 'period_days': days},
            user_id=current_user_id
        )
        
        return jsonify(user_analytics), 200
        
    except Exception as e:
        current_app.logger.error(f"User analytics error: {str(e)}")
        return jsonify({'error': 'Failed to generate user analytics'}), 500

@analytics_bp.route('/analytics/security', methods=['GET'])
@tenant_required(allow_cross_tenant=True)
def get_security_analytics():
    """Get security analytics for current organization"""
    try:
        current_user_id = get_jwt_identity()
        organization_id = TenantContext.get_organization_id()
        
        if not organization_id:
            return jsonify({'error': 'Organization context required'}), 400
        
        # Time filters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Authentication security metrics
        total_login_attempts = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action.in_(['LOGIN_SUCCESS', 'LOGIN_FAILED']),
            AuditLog.timestamp >= start_date
        ).count()
        
        failed_login_attempts = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == 'LOGIN_FAILED',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Account lockout events
        lockout_events = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == 'ACCOUNT_LOCKED',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Permission denied events
        permission_denied = AuditLog.query.filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == 'PERMISSION_DENIED',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Suspicious activity patterns
        suspicious_ips = db.session.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('failed_attempts')
        ).filter(
            AuditLog.organization_id == organization_id,
            AuditLog.action == 'LOGIN_FAILED',
            AuditLog.timestamp >= start_date,
            AuditLog.ip_address.isnot(None)
        ).group_by(AuditLog.ip_address).having(
            func.count(AuditLog.id) >= 5
        ).order_by(func.count(AuditLog.id).desc()).all()
        
        suspicious_ips_data = [
            {
                'ip_address': ip.ip_address,
                'failed_attempts': ip.failed_attempts
            }
            for ip in suspicious_ips
        ]
        
        # Daily security events trend
        security_trend = []
        for i in range(min(days, 30)):  # Limit to 30 days for performance
            day_start = (end_date - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            daily_failed_logins = AuditLog.query.filter(
                AuditLog.organization_id == organization_id,
                AuditLog.action == 'LOGIN_FAILED',
                AuditLog.timestamp >= day_start,
                AuditLog.timestamp < day_end
            ).count()
            
            daily_permission_denied = AuditLog.query.filter(
                AuditLog.organization_id == organization_id,
                AuditLog.action == 'PERMISSION_DENIED',
                AuditLog.timestamp >= day_start,
                AuditLog.timestamp < day_end
            ).count()
            
            security_trend.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'failed_logins': daily_failed_logins,
                'permission_denied': daily_permission_denied
            })
        
        security_trend.reverse()
        
        # Users with recent security events
        users_with_issues = db.session.query(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            func.count(AuditLog.id).label('security_events')
        ).join(AuditLog, User.id == AuditLog.user_id).join(
            User.organizations
        ).filter(
            Organization.id == organization_id,
            AuditLog.action.in_(['LOGIN_FAILED', 'PERMISSION_DENIED', 'ACCOUNT_LOCKED']),
            AuditLog.timestamp >= start_date
        ).group_by(User.id).order_by(
            func.count(AuditLog.id).desc()
        ).limit(20).all()
        
        users_with_issues_data = [
            {
                'user_id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}",
                'security_events': user.security_events
            }
            for user in users_with_issues
        ]
        
        security_analytics = {
            'organization_id': organization_id,
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'authentication_security': {
                'total_login_attempts': total_login_attempts,
                'failed_login_attempts': failed_login_attempts,
                'success_rate': ((total_login_attempts - failed_login_attempts) / total_login_attempts * 100) if total_login_attempts > 0 else 100,
                'lockout_events': lockout_events
            },
            'access_control': {
                'permission_denied_events': permission_denied,
                'suspicious_ips': suspicious_ips_data
            },
            'security_trends': security_trend,
            'users_with_security_issues': users_with_issues_data,
            'risk_assessment': {
                'risk_level': 'high' if failed_login_attempts > 50 or permission_denied > 20 else 'medium' if failed_login_attempts > 10 or permission_denied > 5 else 'low',
                'recommendations': generate_security_recommendations(failed_login_attempts, permission_denied, len(suspicious_ips_data))
            }
        }
        
        log_audit_event(
            action='ANALYTICS_VIEWED',
            resource='analytics',
            details={'type': 'security', 'period_days': days},
            user_id=current_user_id
        )
        
        return jsonify(security_analytics), 200
        
    except Exception as e:
        current_app.logger.error(f"Security analytics error: {str(e)}")
        return jsonify({'error': 'Failed to generate security analytics'}), 500

@analytics_bp.route('/analytics/export', methods=['POST'])
@require_permission('analytics.export')
def export_analytics():
    """Export analytics data for the organization"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        export_type = data.get('type', 'dashboard')  # dashboard, users, security, audit
        format_type = data.get('format', 'json')  # json, csv
        organization_id = data.get('organization_id')
        
        if not organization_id:
            return jsonify({'error': 'Organization ID required'}), 400
        
        # Validate cross-tenant access
        if not validate_cross_tenant_access(organization_id):
            return jsonify({'error': 'Access denied to organization'}), 403
        
        # Set tenant context for export
        organization = Organization.query.get(organization_id)
        if not organization:
            return jsonify({'error': 'Organization not found'}), 404
        
        TenantContext.set_organization(organization_id, organization)
        
        # Generate export data based on type
        if export_type == 'dashboard':
            # Use existing dashboard analytics
            from flask import url_for
            # This would typically call the dashboard analytics function
            export_data = {'message': 'Dashboard export functionality would be implemented here'}
        elif export_type == 'users':
            export_data = {'message': 'User analytics export functionality would be implemented here'}
        elif export_type == 'security':
            export_data = {'message': 'Security analytics export functionality would be implemented here'}
        elif export_type == 'audit':
            # Export audit logs
            days = data.get('days', 30)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            audit_logs = AuditLog.query.filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= start_date
            ).order_by(AuditLog.timestamp.desc()).all()
            
            export_data = {
                'audit_logs': [log.to_dict() for log in audit_logs],
                'organization': organization.to_dict(),
                'export_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                }
            }
        else:
            return jsonify({'error': 'Invalid export type'}), 400
        
        log_audit_event(
            action='ANALYTICS_EXPORTED',
            resource='analytics',
            details={
                'export_type': export_type,
                'format': format_type,
                'organization_id': organization_id
            },
            user_id=current_user_id
        )
        
        return jsonify({
            'message': 'Analytics exported successfully',
            'export_type': export_type,
            'format': format_type,
            'data': export_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Analytics export error: {str(e)}")
        return jsonify({'error': 'Failed to export analytics'}), 500

def generate_security_recommendations(failed_logins, permission_denied, suspicious_ip_count):
    """Generate security recommendations based on metrics"""
    recommendations = []
    
    if failed_logins > 50:
        recommendations.append("High number of failed login attempts detected. Consider implementing additional authentication measures.")
    
    if permission_denied > 20:
        recommendations.append("Frequent permission denied events suggest users may need role adjustments or training.")
    
    if suspicious_ip_count > 5:
        recommendations.append("Multiple suspicious IP addresses detected. Consider implementing IP whitelisting or geographic restrictions.")
    
    if failed_logins > 10:
        recommendations.append("Consider reducing account lockout threshold or implementing CAPTCHA for repeated failures.")
    
    if not recommendations:
        recommendations.append("Security metrics look good. Continue monitoring for any unusual patterns.")
    
    return recommendations
