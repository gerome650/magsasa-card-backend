"""
Partner API key management and integration models
"""

import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.models.user import db, UserStatus, User, Organization

class APIKeyStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"

class PartnerType(Enum):
    INPUT_SUPPLIER = "input_supplier"
    LOGISTICS_PARTNER = "logistics_partner"
    FINANCIAL_PARTNER = "financial_partner"
    BUYER_PROCESSOR = "buyer_processor"
    TECHNOLOGY_PARTNER = "technology_partner"

class RateLimitType(Enum):
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_MONTH = "per_month"

class PartnerAPIKey(db.Model):
    """API keys for partner integrations"""
    __tablename__ = 'partner_api_keys'
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    partner_type = Column(db.Enum(PartnerType), nullable=False)
    
    # API Key details
    key_name = Column(String(100), nullable=False)
    key_prefix = Column(String(20), nullable=False)  # First 8 chars for identification
    key_hash = Column(String(128), nullable=False)   # SHA-256 hash of full key
    
    # Status and lifecycle
    status = Column(db.Enum(APIKeyStatus), default=APIKeyStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    rate_limit_per_hour = Column(Integer, default=1000, nullable=False)
    rate_limit_per_day = Column(Integer, default=10000, nullable=False)
    
    # Permissions and scopes
    allowed_endpoints = Column(Text, nullable=True)  # JSON array of allowed endpoints
    ip_whitelist = Column(Text, nullable=True)       # JSON array of allowed IPs
    
    # Usage tracking
    total_requests = Column(Integer, default=0, nullable=False)
    last_request_ip = Column(String(45), nullable=True)
    last_request_endpoint = Column(String(200), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="api_keys")
    revoked_by_user = relationship("User", foreign_keys=[revoked_by])
    usage_logs = relationship("APIUsageLog", back_populates="api_key", cascade="all, delete-orphan")
    
    def __init__(self, organization_id, partner_type, key_name, **kwargs):
        self.organization_id = organization_id
        self.partner_type = partner_type
        self.key_name = key_name
        
        # Generate API key
        full_key = self.generate_api_key()
        self.key_prefix = full_key[:8]
        self.key_hash = self.hash_key(full_key)
        
        # Set defaults
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @staticmethod
    def generate_api_key():
        """Generate a secure API key"""
        return f"agri_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key):
        """Hash an API key for secure storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def verify_key(self, provided_key):
        """Verify a provided API key against the stored hash"""
        return self.key_hash == self.hash_key(provided_key)
    
    def is_valid(self):
        """Check if the API key is valid and active"""
        if self.status != APIKeyStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            self.status = APIKeyStatus.EXPIRED
            db.session.commit()
            return False
        
        return True
    
    def update_usage(self, endpoint, ip_address):
        """Update usage statistics"""
        self.total_requests += 1
        self.last_used_at = datetime.now(timezone.utc)
        self.last_request_ip = ip_address
        self.last_request_endpoint = endpoint
    
    def revoke(self, revoked_by_user_id, reason=None):
        """Revoke the API key"""
        self.status = APIKeyStatus.REVOKED
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_by = revoked_by_user_id
        
        # Log the revocation
        log = APIUsageLog(
            api_key_id=self.id,
            endpoint="REVOKED",
            method="SYSTEM",
            status_code=0,
            response_time=0,
            ip_address="system",
            user_agent="system",
            request_size=0,
            response_size=0,
            details={"action": "revoked", "reason": reason}
        )
        db.session.add(log)
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'partner_type': self.partner_type.value,
            'key_name': self.key_name,
            'key_prefix': self.key_prefix,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'rate_limits': {
                'per_minute': self.rate_limit_per_minute,
                'per_hour': self.rate_limit_per_hour,
                'per_day': self.rate_limit_per_day
            },
            'usage_stats': {
                'total_requests': self.total_requests,
                'last_request_endpoint': self.last_request_endpoint
            }
        }
        
        if include_sensitive:
            data['allowed_endpoints'] = self.allowed_endpoints
            data['ip_whitelist'] = self.ip_whitelist
            data['last_request_ip'] = self.last_request_ip
        
        return data

class APIUsageLog(db.Model):
    """Log of API usage for monitoring and analytics"""
    __tablename__ = 'api_usage_logs'
    
    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey('partner_api_keys.id'), nullable=False)
    
    # Request details
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Response details
    status_code = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)  # in milliseconds
    
    # Client details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Data size
    request_size = Column(Integer, default=0, nullable=False)   # bytes
    response_size = Column(Integer, default=0, nullable=False)  # bytes
    
    # Additional context
    details = Column(Text, nullable=True)  # JSON for additional context
    
    # Relationships
    api_key = relationship("PartnerAPIKey", back_populates="usage_logs")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'api_key_id': self.api_key_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status_code': self.status_code,
            'response_time': self.response_time,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_size': self.request_size,
            'response_size': self.response_size,
            'details': self.details
        }

class PartnerIntegration(db.Model):
    """Partner integration configurations and settings"""
    __tablename__ = 'partner_integrations'
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    partner_type = Column(db.Enum(PartnerType), nullable=False)
    
    # Integration details
    integration_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(db.Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(128), nullable=True)
    callback_url = Column(String(500), nullable=True)
    
    # Data sync settings
    sync_enabled = Column(Boolean, default=False, nullable=False)
    sync_frequency = Column(String(20), default="hourly", nullable=False)  # hourly, daily, weekly
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    
    # Business settings
    commission_rate = Column(Float, default=0.0, nullable=False)  # Percentage
    minimum_order_value = Column(Float, default=0.0, nullable=False)
    maximum_order_value = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    activated_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="partner_integrations")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'partner_type': self.partner_type.value,
            'integration_name': self.integration_name,
            'description': self.description,
            'status': self.status.value,
            'webhook_url': self.webhook_url,
            'callback_url': self.callback_url,
            'sync_settings': {
                'enabled': self.sync_enabled,
                'frequency': self.sync_frequency,
                'last_sync': self.last_sync_at.isoformat() if self.last_sync_at else None,
                'next_sync': self.next_sync_at.isoformat() if self.next_sync_at else None
            },
            'business_settings': {
                'commission_rate': self.commission_rate,
                'minimum_order_value': self.minimum_order_value,
                'maximum_order_value': self.maximum_order_value
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None
        }

class WebhookEvent(db.Model):
    """Webhook events for partner integrations"""
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True)
    integration_id = Column(Integer, ForeignKey('partner_integrations.id'), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # order_created, payment_completed, etc.
    event_data = Column(Text, nullable=False)        # JSON payload
    
    # Delivery details
    webhook_url = Column(String(500), nullable=False)
    delivery_attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    
    # Status tracking
    status = Column(String(20), default="pending", nullable=False)  # pending, delivered, failed
    last_attempt_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Response details
    last_response_code = Column(Integer, nullable=True)
    last_response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    integration = relationship("PartnerIntegration")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'integration_id': self.integration_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'webhook_url': self.webhook_url,
            'delivery_status': {
                'status': self.status,
                'attempts': self.delivery_attempts,
                'max_attempts': self.max_attempts,
                'last_attempt': self.last_attempt_at.isoformat() if self.last_attempt_at else None,
                'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
            },
            'response_details': {
                'last_response_code': self.last_response_code,
                'error_message': self.error_message
            },
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Add relationships to existing models
def add_partner_relationships():
    """Add partner-related relationships to existing models"""
    from src.models.user import Organization
    
    # Add to Organization model
    if not hasattr(Organization, 'api_keys'):
        Organization.api_keys = relationship("PartnerAPIKey", back_populates="organization", cascade="all, delete-orphan")
    
    if not hasattr(Organization, 'partner_integrations'):
        Organization.partner_integrations = relationship("PartnerIntegration", back_populates="organization", cascade="all, delete-orphan")

# Rate limiting helper functions
class RateLimiter:
    """Rate limiting utilities for API keys"""
    
    @staticmethod
    def check_rate_limit(api_key, limit_type=RateLimitType.PER_MINUTE):
        """Check if API key has exceeded rate limits"""
        now = datetime.now(timezone.utc)
        
        if limit_type == RateLimitType.PER_MINUTE:
            time_window = now - timedelta(minutes=1)
            limit = api_key.rate_limit_per_minute
        elif limit_type == RateLimitType.PER_HOUR:
            time_window = now - timedelta(hours=1)
            limit = api_key.rate_limit_per_hour
        elif limit_type == RateLimitType.PER_DAY:
            time_window = now - timedelta(days=1)
            limit = api_key.rate_limit_per_day
        else:
            return True  # Unknown limit type, allow
        
        # Count requests in time window
        request_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.timestamp >= time_window
        ).count()
        
        return request_count < limit
    
    @staticmethod
    def get_rate_limit_status(api_key):
        """Get current rate limit status for an API key"""
        now = datetime.now(timezone.utc)
        
        # Check all time windows
        minute_window = now - timedelta(minutes=1)
        hour_window = now - timedelta(hours=1)
        day_window = now - timedelta(days=1)
        
        minute_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.timestamp >= minute_window
        ).count()
        
        hour_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.timestamp >= hour_window
        ).count()
        
        day_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.timestamp >= day_window
        ).count()
        
        return {
            'per_minute': {
                'used': minute_count,
                'limit': api_key.rate_limit_per_minute,
                'remaining': max(0, api_key.rate_limit_per_minute - minute_count)
            },
            'per_hour': {
                'used': hour_count,
                'limit': api_key.rate_limit_per_hour,
                'remaining': max(0, api_key.rate_limit_per_hour - hour_count)
            },
            'per_day': {
                'used': day_count,
                'limit': api_key.rate_limit_per_day,
                'remaining': max(0, api_key.rate_limit_per_day - day_count)
            }
        }
