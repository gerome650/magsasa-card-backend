from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timezone
from enum import Enum

db = SQLAlchemy()
bcrypt = Bcrypt()

class UserRole(Enum):
    # Administrative Tier
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    
    # Operational Tier
    FIELD_OFFICER = "field_officer"
    FARMER = "farmer"
    
    # Partner Tier
    INPUT_SUPPLIER = "input_supplier"
    LOGISTICS_PARTNER = "logistics_partner"
    FINANCIAL_PARTNER = "financial_partner"
    BUYER_PROCESSOR = "buyer_processor"

class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

# Association table for many-to-many relationship between users and organizations
user_organizations = db.Table('user_organizations',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organization.id'), primary_key=True),
    db.Column('role', db.Enum(UserRole), nullable=False),
    db.Column('created_at', db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.Column('is_primary', db.Boolean, default=False)
)

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'internal', 'partner', 'client'
    description = db.Column(db.Text)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    users = db.relationship('User', secondary=user_organizations, back_populates='organizations')
    
    # Agricultural relationships (will be populated when agricultural models are imported)
    # agricultural_org = relationship("AgriculturalOrganization", back_populates="organization", uselist=False)
    
    def __repr__(self):
        return f'<Organization {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'type': self.type,
            'description': self.description,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'address': self.address,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING)
    last_login = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organizations = db.relationship('Organization', secondary=user_organizations, back_populates='users')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    sessions = db.relationship('UserSession', backref='user', lazy=True)
    
    # Agricultural relationships (will be populated when agricultural models are imported)
    # farmer_profile = relationship("Farmer", back_populates="user", uselist=False)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if the provided password matches the user's password"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_primary_organization(self):
        """Get the user's primary organization"""
        for org in self.organizations:
            # Check if this is the primary organization for this user
            association = db.session.query(user_organizations).filter_by(
                user_id=self.id, 
                organization_id=org.id, 
                is_primary=True
            ).first()
            if association:
                return org
        return None
    
    def get_role_in_organization(self, organization_id):
        """Get the user's role in a specific organization"""
        association = db.session.query(user_organizations).filter_by(
            user_id=self.id, 
            organization_id=organization_id
        ).first()
        return association.role if association else None
    
    def has_permission(self, permission, organization_id=None):
        """Check if user has a specific permission"""
        # Get user's role in the organization
        if organization_id:
            role = self.get_role_in_organization(organization_id)
        else:
            # Use primary organization if no specific org provided
            primary_org = self.get_primary_organization()
            role = self.get_role_in_organization(primary_org.id) if primary_org else None
        
        if not role:
            return False
        
        # Check if role has the required permission
        role_permissions = Permission.query.filter_by(role=role).all()
        return any(perm.name == permission for perm in role_permissions)
    
    def to_dict(self, include_organizations=False):
        result = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'status': self.status.value,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_organizations:
            result['organizations'] = []
            for org in self.organizations:
                role = self.get_role_in_organization(org.id)
                result['organizations'].append({
                    'organization': org.to_dict(),
                    'role': role.value if role else None,
                    'is_primary': org.id == (self.get_primary_organization().id if self.get_primary_organization() else None)
                })
        
        return result

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    resource = db.Column(db.String(100), nullable=False)  # e.g., 'users', 'farms', 'reports'
    action = db.Column(db.String(50), nullable=False)     # e.g., 'create', 'read', 'update', 'delete'
    role = db.Column(db.Enum(UserRole), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Permission {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'resource': self.resource,
            'action': self.action,
            'role': self.role.value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<UserSession {self.session_token}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.String(100))
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.resource}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
