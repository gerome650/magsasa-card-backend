"""
Tenant data migration and management utilities
"""

import json
import csv
import io
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from flask import current_app

from src.models.user import (
    db, User, Organization, Permission, UserRole, UserStatus,
    AuditLog, UserSession, user_organizations
)

class TenantMigrationManager:
    """Manages data migration operations for multi-tenant organizations"""
    
    def __init__(self):
        self.supported_formats = ['json', 'csv']
        self.exportable_models = ['users', 'audit_logs', 'sessions', 'permissions']
    
    def export_organization_data(self, organization_id: int, 
                                include_models: List[str] = None,
                                format_type: str = 'json',
                                date_range: tuple = None) -> Dict[str, Any]:
        """
        Export all data for an organization
        
        Args:
            organization_id: ID of the organization to export
            include_models: List of models to include in export
            format_type: Export format ('json' or 'csv')
            date_range: Tuple of (start_date, end_date) for filtering
        
        Returns:
            Dictionary containing exported data
        """
        try:
            organization = Organization.query.get(organization_id)
            if not organization:
                raise ValueError(f"Organization {organization_id} not found")
            
            if include_models is None:
                include_models = self.exportable_models
            
            export_data = {
                'organization': organization.to_dict(),
                'export_metadata': {
                    'exported_at': datetime.now(timezone.utc).isoformat(),
                    'format': format_type,
                    'models_included': include_models,
                    'date_range': {
                        'start': date_range[0].isoformat() if date_range and date_range[0] else None,
                        'end': date_range[1].isoformat() if date_range and date_range[1] else None
                    } if date_range else None
                },
                'data': {}
            }
            
            # Export users
            if 'users' in include_models:
                users_data = []
                for user in organization.users:
                    user_dict = user.to_dict(include_organizations=True)
                    # Add organization-specific role
                    user_dict['role_in_organization'] = user.get_role_in_organization(organization_id).value
                    users_data.append(user_dict)
                export_data['data']['users'] = users_data
            
            # Export audit logs
            if 'audit_logs' in include_models:
                audit_query = AuditLog.query.filter_by(organization_id=organization_id)
                
                if date_range:
                    if date_range[0]:
                        audit_query = audit_query.filter(AuditLog.timestamp >= date_range[0])
                    if date_range[1]:
                        audit_query = audit_query.filter(AuditLog.timestamp <= date_range[1])
                
                audit_logs = audit_query.order_by(AuditLog.timestamp.desc()).all()
                export_data['data']['audit_logs'] = [log.to_dict() for log in audit_logs]
            
            # Export user sessions
            if 'sessions' in include_models:
                sessions_data = []
                for user in organization.users:
                    user_sessions = UserSession.query.filter_by(user_id=user.id).all()
                    for session in user_sessions:
                        session_dict = session.to_dict()
                        session_dict['username'] = user.username
                        sessions_data.append(session_dict)
                export_data['data']['sessions'] = sessions_data
            
            # Export permissions (role-based)
            if 'permissions' in include_models:
                # Get all roles used in this organization
                org_roles = set()
                for user in organization.users:
                    role = user.get_role_in_organization(organization_id)
                    if role:
                        org_roles.add(role)
                
                permissions_data = []
                for role in org_roles:
                    role_permissions = Permission.query.filter_by(role=role).all()
                    for perm in role_permissions:
                        permissions_data.append(perm.to_dict())
                
                export_data['data']['permissions'] = permissions_data
            
            return export_data
            
        except Exception as e:
            current_app.logger.error(f"Export error for organization {organization_id}: {str(e)}")
            raise
    
    def import_organization_data(self, import_data: Dict[str, Any],
                                target_organization_id: int = None,
                                merge_strategy: str = 'skip_existing') -> Dict[str, Any]:
        """
        Import data into an organization
        
        Args:
            import_data: Data to import (from export_organization_data)
            target_organization_id: Target organization ID (None to create new)
            merge_strategy: How to handle existing data ('skip_existing', 'update_existing', 'replace_all')
        
        Returns:
            Import results summary
        """
        try:
            results = {
                'organization_id': target_organization_id,
                'imported_counts': {},
                'errors': [],
                'warnings': []
            }
            
            # Create or get target organization
            if target_organization_id is None:
                # Create new organization
                org_data = import_data.get('organization', {})
                new_org = Organization(
                    name=f"{org_data.get('name', 'Imported Org')} (Imported)",
                    code=f"{org_data.get('code', 'IMPORTED')}_{datetime.now().strftime('%Y%m%d')}",
                    type=org_data.get('type', 'internal'),
                    description=f"Imported from {org_data.get('name', 'unknown')} on {datetime.now().strftime('%Y-%m-%d')}",
                    status=UserStatus.ACTIVE
                )
                db.session.add(new_org)
                db.session.flush()
                target_organization_id = new_org.id
                results['organization_id'] = target_organization_id
                results['created_new_organization'] = True
            else:
                target_org = Organization.query.get(target_organization_id)
                if not target_org:
                    raise ValueError(f"Target organization {target_organization_id} not found")
                results['created_new_organization'] = False
            
            data = import_data.get('data', {})
            
            # Import users
            if 'users' in data:
                imported_users = 0
                for user_data in data['users']:
                    try:
                        existing_user = User.query.filter_by(username=user_data['username']).first()
                        
                        if existing_user and merge_strategy == 'skip_existing':
                            results['warnings'].append(f"Skipped existing user: {user_data['username']}")
                            continue
                        
                        if not existing_user:
                            # Create new user
                            new_user = User(
                                username=user_data['username'],
                                email=user_data['email'],
                                first_name=user_data['first_name'],
                                last_name=user_data['last_name'],
                                phone=user_data.get('phone'),
                                status=UserStatus(user_data.get('status', 'active')),
                                email_verified=user_data.get('email_verified', False)
                            )
                            # Set a default password (should be changed on first login)
                            new_user.set_password('TempPassword123!')
                            db.session.add(new_user)
                            db.session.flush()
                            
                            # Add to organization
                            role = UserRole(user_data.get('role_in_organization', 'farmer'))
                            association = user_organizations.insert().values(
                                user_id=new_user.id,
                                organization_id=target_organization_id,
                                role=role,
                                is_primary=True
                            )
                            db.session.execute(association)
                            imported_users += 1
                        
                        elif merge_strategy == 'update_existing':
                            # Update existing user
                            existing_user.first_name = user_data['first_name']
                            existing_user.last_name = user_data['last_name']
                            existing_user.phone = user_data.get('phone')
                            # Add to organization if not already there
                            if not existing_user.get_role_in_organization(target_organization_id):
                                role = UserRole(user_data.get('role_in_organization', 'farmer'))
                                association = user_organizations.insert().values(
                                    user_id=existing_user.id,
                                    organization_id=target_organization_id,
                                    role=role,
                                    is_primary=False
                                )
                                db.session.execute(association)
                            imported_users += 1
                    
                    except Exception as e:
                        results['errors'].append(f"Failed to import user {user_data.get('username', 'unknown')}: {str(e)}")
                
                results['imported_counts']['users'] = imported_users
            
            # Import audit logs (if requested and merge_strategy allows)
            if 'audit_logs' in data and merge_strategy != 'skip_existing':
                imported_logs = 0
                for log_data in data['audit_logs']:
                    try:
                        # Create new audit log with updated organization_id
                        new_log = AuditLog(
                            user_id=log_data.get('user_id'),
                            organization_id=target_organization_id,
                            action=log_data['action'],
                            resource=log_data['resource'],
                            resource_id=log_data.get('resource_id'),
                            details=log_data.get('details'),
                            ip_address=log_data.get('ip_address'),
                            user_agent=log_data.get('user_agent'),
                            timestamp=datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00'))
                        )
                        db.session.add(new_log)
                        imported_logs += 1
                    except Exception as e:
                        results['errors'].append(f"Failed to import audit log: {str(e)}")
                
                results['imported_counts']['audit_logs'] = imported_logs
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Import error: {str(e)}")
            raise
    
    def clone_organization(self, source_org_id: int, new_org_name: str,
                          new_org_code: str, include_users: bool = True,
                          include_audit_logs: bool = False) -> Dict[str, Any]:
        """
        Clone an organization with its data
        
        Args:
            source_org_id: Source organization ID
            new_org_name: Name for the new organization
            new_org_code: Code for the new organization
            include_users: Whether to clone users
            include_audit_logs: Whether to clone audit logs
        
        Returns:
            Clone operation results
        """
        try:
            # Export source organization
            include_models = []
            if include_users:
                include_models.extend(['users', 'permissions'])
            if include_audit_logs:
                include_models.append('audit_logs')
            
            export_data = self.export_organization_data(
                source_org_id,
                include_models=include_models
            )
            
            # Modify organization data for clone
            export_data['organization']['name'] = new_org_name
            export_data['organization']['code'] = new_org_code
            export_data['organization']['description'] = f"Cloned from {export_data['organization']['name']}"
            
            # Import into new organization
            results = self.import_organization_data(
                export_data,
                target_organization_id=None,  # Create new
                merge_strategy='replace_all'
            )
            
            results['clone_source_id'] = source_org_id
            results['clone_operation'] = True
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Clone error: {str(e)}")
            raise
    
    def generate_organization_report(self, organization_id: int) -> Dict[str, Any]:
        """
        Generate a comprehensive report for an organization
        
        Args:
            organization_id: Organization ID
        
        Returns:
            Comprehensive organization report
        """
        try:
            organization = Organization.query.get(organization_id)
            if not organization:
                raise ValueError(f"Organization {organization_id} not found")
            
            # Basic organization info
            report = {
                'organization': organization.to_dict(),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'summary': {},
                'details': {}
            }
            
            # User statistics
            total_users = len(organization.users)
            active_users = len([u for u in organization.users if u.status == UserStatus.ACTIVE])
            
            # Role distribution
            role_distribution = {}
            for user in organization.users:
                role = user.get_role_in_organization(organization_id)
                if role:
                    role_name = role.value
                    role_distribution[role_name] = role_distribution.get(role_name, 0) + 1
            
            # Recent activity (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_activity = AuditLog.query.filter(
                AuditLog.organization_id == organization_id,
                AuditLog.timestamp >= thirty_days_ago
            ).count()
            
            # Security metrics
            failed_logins = AuditLog.query.filter(
                AuditLog.organization_id == organization_id,
                AuditLog.action == 'LOGIN_FAILED',
                AuditLog.timestamp >= thirty_days_ago
            ).count()
            
            locked_accounts = User.query.join(User.organizations).filter(
                Organization.id == organization_id,
                User.account_locked_until > datetime.now(timezone.utc)
            ).count()
            
            report['summary'] = {
                'total_users': total_users,
                'active_users': active_users,
                'user_activity_rate': (active_users / total_users * 100) if total_users > 0 else 0,
                'role_distribution': role_distribution,
                'recent_activity_count': recent_activity,
                'security_metrics': {
                    'failed_logins_30d': failed_logins,
                    'locked_accounts': locked_accounts
                }
            }
            
            # Detailed breakdowns
            report['details'] = {
                'users_by_status': {},
                'users_by_role': role_distribution,
                'recent_user_registrations': [],
                'top_active_users': []
            }
            
            # Users by status
            for status in UserStatus:
                count = len([u for u in organization.users if u.status == status])
                report['details']['users_by_status'][status.value] = count
            
            # Recent registrations (last 30 days)
            recent_users = [
                {
                    'username': u.username,
                    'full_name': f"{u.first_name} {u.last_name}",
                    'created_at': u.created_at.isoformat() if u.created_at else None,
                    'role': u.get_role_in_organization(organization_id).value
                }
                for u in organization.users
                if u.created_at and u.created_at >= thirty_days_ago
            ]
            report['details']['recent_user_registrations'] = recent_users
            
            return report
            
        except Exception as e:
            current_app.logger.error(f"Report generation error: {str(e)}")
            raise
    
    def validate_organization_data(self, organization_id: int) -> Dict[str, Any]:
        """
        Validate organization data integrity
        
        Args:
            organization_id: Organization ID to validate
        
        Returns:
            Validation results
        """
        try:
            organization = Organization.query.get(organization_id)
            if not organization:
                raise ValueError(f"Organization {organization_id} not found")
            
            validation_results = {
                'organization_id': organization_id,
                'validation_date': datetime.now(timezone.utc).isoformat(),
                'is_valid': True,
                'issues': [],
                'warnings': [],
                'statistics': {}
            }
            
            # Check for orphaned users
            orphaned_users = []
            for user in organization.users:
                if not user.get_role_in_organization(organization_id):
                    orphaned_users.append(user.username)
                    validation_results['issues'].append(f"User {user.username} has no role in organization")
            
            # Check for users without primary organization
            users_without_primary = []
            for user in organization.users:
                if not user.get_primary_organization():
                    users_without_primary.append(user.username)
                    validation_results['warnings'].append(f"User {user.username} has no primary organization")
            
            # Check for inactive admin users
            admin_users = [
                u for u in organization.users
                if u.get_role_in_organization(organization_id) in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            ]
            inactive_admins = [u for u in admin_users if u.status != UserStatus.ACTIVE]
            
            if inactive_admins:
                validation_results['warnings'].extend([
                    f"Admin user {u.username} is not active" for u in inactive_admins
                ])
            
            # Check if organization has at least one admin
            if not admin_users:
                validation_results['issues'].append("Organization has no admin users")
                validation_results['is_valid'] = False
            
            validation_results['statistics'] = {
                'total_users': len(organization.users),
                'orphaned_users': len(orphaned_users),
                'users_without_primary_org': len(users_without_primary),
                'admin_users': len(admin_users),
                'inactive_admin_users': len(inactive_admins)
            }
            
            if validation_results['issues']:
                validation_results['is_valid'] = False
            
            return validation_results
            
        except Exception as e:
            current_app.logger.error(f"Validation error: {str(e)}")
            raise
