"""
Enhanced audit trail and monitoring system models
"""

import json
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.models.user import db

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class MonitoringMetricType(Enum):
    SYSTEM_PERFORMANCE = "system_performance"
    SECURITY_EVENT = "security_event"
    USER_ACTIVITY = "user_activity"
    API_USAGE = "api_usage"
    BUSINESS_METRIC = "business_metric"

class ComplianceReportType(Enum):
    GDPR_ACCESS_LOG = "gdpr_access_log"
    SOX_FINANCIAL_CONTROLS = "sox_financial_controls"
    AUDIT_TRAIL_SUMMARY = "audit_trail_summary"
    SECURITY_INCIDENT_REPORT = "security_incident_report"
    USER_ACCESS_REVIEW = "user_access_review"

class EnhancedAuditLog(db.Model):
    """Enhanced audit log with additional context and correlation"""
    __tablename__ = 'enhanced_audit_logs'
    
    id = Column(Integer, primary_key=True)
    
    # Basic audit information
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=True)
    session_id = Column(String(128), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    
    # Enhanced context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_url = Column(String(500), nullable=True)
    response_status = Column(Integer, nullable=True)
    
    # Timing and performance
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    duration_ms = Column(Float, nullable=True)  # Request duration in milliseconds
    
    # Data and context
    old_values = Column(Text, nullable=True)  # JSON of previous values
    new_values = Column(Text, nullable=True)  # JSON of new values
    additional_context = Column(Text, nullable=True)  # JSON of additional context
    
    # Risk and security
    risk_score = Column(Float, default=0.0, nullable=False)  # 0-100 risk score
    security_flags = Column(Text, nullable=True)  # JSON array of security flags
    
    # Correlation and tracking
    correlation_id = Column(String(128), nullable=True)  # For tracking related events
    parent_event_id = Column(Integer, ForeignKey('enhanced_audit_logs.id'), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    parent_event = relationship("EnhancedAuditLog", remote_side=[id])
    child_events = relationship("EnhancedAuditLog", back_populates="parent_event")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_enhanced_audit_timestamp', 'timestamp'),
        Index('idx_enhanced_audit_user_org', 'user_id', 'organization_id'),
        Index('idx_enhanced_audit_action', 'action'),
        Index('idx_enhanced_audit_correlation', 'correlation_id'),
        Index('idx_enhanced_audit_risk', 'risk_score'),
    )
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'session_id': self.session_id,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration_ms': self.duration_ms,
            'risk_score': self.risk_score,
            'correlation_id': self.correlation_id,
            'response_status': self.response_status
        }
        
        if include_sensitive:
            data.update({
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'request_method': self.request_method,
                'request_url': self.request_url,
                'old_values': self.old_values,
                'new_values': self.new_values,
                'additional_context': self.additional_context,
                'security_flags': self.security_flags
            })
        
        return data

class SecurityAlert(db.Model):
    """Security alerts and incidents"""
    __tablename__ = 'security_alerts'
    
    id = Column(Integer, primary_key=True)
    
    # Alert identification
    alert_type = Column(String(100), nullable=False)
    severity = Column(db.Enum(AlertSeverity), nullable=False)
    status = Column(db.Enum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    
    # Alert details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    
    # Context and correlation
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    related_audit_log_id = Column(Integer, ForeignKey('enhanced_audit_logs.id'), nullable=True)
    correlation_id = Column(String(128), nullable=True)
    
    # Detection and response
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Alert data
    alert_data = Column(Text, nullable=True)  # JSON of alert-specific data
    response_actions = Column(Text, nullable=True)  # JSON of actions taken
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    user = relationship("User", foreign_keys=[user_id])
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    related_audit_log = relationship("EnhancedAuditLog", foreign_keys=[related_audit_log_id])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'status': self.status.value,
            'title': self.title,
            'description': self.description,
            'recommendation': self.recommendation,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'correlation_id': self.correlation_id,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'alert_data': self.alert_data,
            'response_actions': self.response_actions
        }

class MonitoringMetric(db.Model):
    """System monitoring metrics and KPIs"""
    __tablename__ = 'monitoring_metrics'
    
    id = Column(Integer, primary_key=True)
    
    # Metric identification
    metric_name = Column(String(100), nullable=False)
    metric_type = Column(db.Enum(MonitoringMetricType), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=True)
    
    # Metric values
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    threshold_warning = Column(Float, nullable=True)
    threshold_critical = Column(Float, nullable=True)
    
    # Context and metadata
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    tags = Column(Text, nullable=True)  # JSON of key-value tags
    metadata = Column(Text, nullable=True)  # JSON of additional metadata
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_monitoring_metric_name_time', 'metric_name', 'timestamp'),
        Index('idx_monitoring_metric_org_type', 'organization_id', 'metric_type'),
        Index('idx_monitoring_metric_timestamp', 'timestamp'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_type': self.metric_type.value,
            'organization_id': self.organization_id,
            'value': self.value,
            'unit': self.unit,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'tags': self.tags,
            'metadata': self.metadata
        }

class ComplianceReport(db.Model):
    """Compliance and regulatory reports"""
    __tablename__ = 'compliance_reports'
    
    id = Column(Integer, primary_key=True)
    
    # Report identification
    report_type = Column(db.Enum(ComplianceReportType), nullable=False)
    report_name = Column(String(200), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    
    # Report period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Report generation
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    generated_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Report content
    report_data = Column(Text, nullable=False)  # JSON of report data
    summary = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)  # JSON of compliance findings
    recommendations = Column(Text, nullable=True)  # JSON of recommendations
    
    # Report status
    status = Column(String(20), default='generated', nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # File storage
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    generated_by_user = relationship("User", foreign_keys=[generated_by])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'report_type': self.report_type.value,
            'report_name': self.report_name,
            'organization_id': self.organization_id,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'generated_by': self.generated_by,
            'status': self.status,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'summary': self.summary
        }

class SystemHealthCheck(db.Model):
    """System health monitoring and diagnostics"""
    __tablename__ = 'system_health_checks'
    
    id = Column(Integer, primary_key=True)
    
    # Health check details
    check_name = Column(String(100), nullable=False)
    check_type = Column(String(50), nullable=False)  # database, api, external_service, etc.
    
    # Status and results
    status = Column(String(20), nullable=False)  # healthy, warning, critical, unknown
    response_time_ms = Column(Float, nullable=True)
    
    # Check results
    details = Column(Text, nullable=True)  # JSON of detailed results
    error_message = Column(Text, nullable=True)
    
    # Timing
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_health_check_name_time', 'check_name', 'checked_at'),
        Index('idx_health_check_status', 'status'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'check_name': self.check_name,
            'check_type': self.check_type,
            'status': self.status,
            'response_time_ms': self.response_time_ms,
            'details': self.details,
            'error_message': self.error_message,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None
        }

class AuditLogArchive(db.Model):
    """Archived audit logs for long-term storage"""
    __tablename__ = 'audit_log_archives'
    
    id = Column(Integer, primary_key=True)
    
    # Archive details
    archive_name = Column(String(200), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    
    # Archive period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Archive metadata
    total_records = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    compression_type = Column(String(20), default='gzip', nullable=False)
    
    # Archive creation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Verification
    checksum = Column(String(128), nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'archive_name': self.archive_name,
            'organization_id': self.organization_id,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'total_records': self.total_records,
            'file_size': self.file_size,
            'compression_type': self.compression_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'checksum': self.checksum,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }

# Utility functions for monitoring and alerting
class MonitoringUtils:
    """Utility functions for monitoring and alerting"""
    
    @staticmethod
    def calculate_risk_score(action, resource, user_context, request_context):
        """Calculate risk score for an audit event"""
        risk_score = 0.0
        
        # Base risk by action type
        high_risk_actions = ['DELETE', 'REVOKE', 'DISABLE', 'EXPORT', 'ADMIN_ACCESS']
        medium_risk_actions = ['UPDATE', 'CREATE', 'LOGIN', 'PERMISSION_CHANGE']
        
        if any(risk_action in action.upper() for risk_action in high_risk_actions):
            risk_score += 30.0
        elif any(risk_action in action.upper() for risk_action in medium_risk_actions):
            risk_score += 15.0
        else:
            risk_score += 5.0
        
        # Risk by resource sensitivity
        sensitive_resources = ['USER', 'PERMISSION', 'API_KEY', 'ORGANIZATION']
        if any(sensitive in resource.upper() for sensitive in sensitive_resources):
            risk_score += 20.0
        
        # Risk by user context
        if user_context.get('is_admin'):
            risk_score += 10.0
        if user_context.get('failed_login_attempts', 0) > 0:
            risk_score += user_context['failed_login_attempts'] * 5.0
        
        # Risk by request context
        if request_context.get('unusual_time'):  # Outside business hours
            risk_score += 15.0
        if request_context.get('unusual_location'):  # Different IP/location
            risk_score += 25.0
        if request_context.get('multiple_rapid_requests'):
            risk_score += 20.0
        
        return min(risk_score, 100.0)  # Cap at 100
    
    @staticmethod
    def detect_security_anomalies(audit_logs, time_window_hours=24):
        """Detect security anomalies in audit logs"""
        anomalies = []
        
        # Group logs by user and analyze patterns
        user_activities = {}
        for log in audit_logs:
            user_id = log.user_id
            if user_id not in user_activities:
                user_activities[user_id] = []
            user_activities[user_id].append(log)
        
        for user_id, activities in user_activities.items():
            # Check for unusual activity patterns
            if len(activities) > 100:  # Too many actions
                anomalies.append({
                    'type': 'excessive_activity',
                    'user_id': user_id,
                    'count': len(activities),
                    'severity': 'medium'
                })
            
            # Check for failed login attempts
            failed_logins = [a for a in activities if 'LOGIN_FAILED' in a.action]
            if len(failed_logins) > 5:
                anomalies.append({
                    'type': 'multiple_failed_logins',
                    'user_id': user_id,
                    'count': len(failed_logins),
                    'severity': 'high'
                })
            
            # Check for privilege escalation attempts
            admin_actions = [a for a in activities if 'ADMIN' in a.action or 'PERMISSION' in a.action]
            if len(admin_actions) > 10:
                anomalies.append({
                    'type': 'potential_privilege_escalation',
                    'user_id': user_id,
                    'count': len(admin_actions),
                    'severity': 'critical'
                })
        
        return anomalies
    
    @staticmethod
    def generate_compliance_summary(audit_logs, report_type):
        """Generate compliance summary from audit logs"""
        summary = {
            'total_events': len(audit_logs),
            'unique_users': len(set(log.user_id for log in audit_logs if log.user_id)),
            'unique_organizations': len(set(log.organization_id for log in audit_logs if log.organization_id)),
            'high_risk_events': len([log for log in audit_logs if log.risk_score > 70]),
            'security_events': len([log for log in audit_logs if 'SECURITY' in log.action or log.risk_score > 50])
        }
        
        # Report-specific analysis
        if report_type == ComplianceReportType.GDPR_ACCESS_LOG:
            summary['data_access_events'] = len([log for log in audit_logs if 'READ' in log.action or 'EXPORT' in log.action])
            summary['data_modification_events'] = len([log for log in audit_logs if 'UPDATE' in log.action or 'DELETE' in log.action])
        
        elif report_type == ComplianceReportType.SECURITY_INCIDENT_REPORT:
            summary['failed_authentications'] = len([log for log in audit_logs if 'LOGIN_FAILED' in log.action])
            summary['unauthorized_access_attempts'] = len([log for log in audit_logs if log.response_status == 403])
        
        return summary
