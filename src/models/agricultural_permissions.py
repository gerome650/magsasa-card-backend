"""
MAGSASA-CARD Enhanced Platform - Agricultural Permission System
Enhanced permission system with agricultural-specific permissions and role mappings
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Set
import json

class AgriculturalPermission(Enum):
    """Agricultural-specific permissions for comprehensive farm operations"""
    
    # Farmer Management Permissions
    FARMER_VIEW_ALL = "farmer:view:all"
    FARMER_VIEW_OWN = "farmer:view:own"
    FARMER_CREATE = "farmer:create"
    FARMER_UPDATE_ALL = "farmer:update:all"
    FARMER_UPDATE_OWN = "farmer:update:own"
    FARMER_DELETE = "farmer:delete"
    FARMER_VERIFY = "farmer:verify"
    FARMER_EXPORT = "farmer:export"
    
    # Farm Management Permissions
    FARM_VIEW_ALL = "farm:view:all"
    FARM_VIEW_OWN = "farm:view:own"
    FARM_CREATE = "farm:create"
    FARM_UPDATE_ALL = "farm:update:all"
    FARM_UPDATE_OWN = "farm:update:own"
    FARM_DELETE = "farm:delete"
    FARM_EXPORT = "farm:export"
    
    # Field Management Permissions
    FIELD_VIEW_ALL = "field:view:all"
    FIELD_VIEW_OWN = "field:view:own"
    FIELD_CREATE = "field:create"
    FIELD_UPDATE_ALL = "field:update:all"
    FIELD_UPDATE_OWN = "field:update:own"
    FIELD_DELETE = "field:delete"
    
    # Crop Management Permissions
    CROP_VIEW = "crop:view"
    CROP_CREATE = "crop:create"
    CROP_UPDATE = "crop:update"
    CROP_DELETE = "crop:delete"
    CROP_MANAGE_CATALOG = "crop:manage:catalog"
    
    # Farm Activity Permissions
    ACTIVITY_VIEW_ALL = "activity:view:all"
    ACTIVITY_VIEW_OWN = "activity:view:own"
    ACTIVITY_CREATE = "activity:create"
    ACTIVITY_UPDATE_ALL = "activity:update:all"
    ACTIVITY_UPDATE_OWN = "activity:update:own"
    ACTIVITY_DELETE = "activity:delete"
    ACTIVITY_APPROVE = "activity:approve"
    ACTIVITY_EXPORT = "activity:export"
    
    # Agricultural Input Permissions
    INPUT_VIEW_CATALOG = "input:view:catalog"
    INPUT_VIEW_PRICING = "input:view:pricing"
    INPUT_CREATE = "input:create"
    INPUT_UPDATE = "input:update"
    INPUT_DELETE = "input:delete"
    INPUT_MANAGE_STOCK = "input:manage:stock"
    INPUT_MANAGE_PRICING = "input:manage:pricing"
    INPUT_APPROVE_ORDERS = "input:approve:orders"
    
    # Transaction Permissions
    TRANSACTION_VIEW_ALL = "transaction:view:all"
    TRANSACTION_VIEW_OWN = "transaction:view:own"
    TRANSACTION_CREATE = "transaction:create"
    TRANSACTION_UPDATE = "transaction:update"
    TRANSACTION_APPROVE = "transaction:approve"
    TRANSACTION_CANCEL = "transaction:cancel"
    TRANSACTION_EXPORT = "transaction:export"
    
    # Harvest Management Permissions
    HARVEST_VIEW_ALL = "harvest:view:all"
    HARVEST_VIEW_OWN = "harvest:view:own"
    HARVEST_CREATE = "harvest:create"
    HARVEST_UPDATE_ALL = "harvest:update:all"
    HARVEST_UPDATE_OWN = "harvest:update:own"
    HARVEST_DELETE = "harvest:delete"
    HARVEST_EXPORT = "harvest:export"
    
    # Weather Data Permissions
    WEATHER_VIEW = "weather:view"
    WEATHER_CREATE = "weather:create"
    WEATHER_UPDATE = "weather:update"
    WEATHER_DELETE = "weather:delete"
    
    # Analytics and Reporting Permissions
    ANALYTICS_VIEW_BASIC = "analytics:view:basic"
    ANALYTICS_VIEW_ADVANCED = "analytics:view:advanced"
    ANALYTICS_VIEW_FINANCIAL = "analytics:view:financial"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_CREATE_REPORTS = "analytics:create:reports"
    
    # Partner Integration Permissions
    PARTNER_VIEW_CATALOG = "partner:view:catalog"
    PARTNER_PLACE_ORDERS = "partner:place:orders"
    PARTNER_MANAGE_ORDERS = "partner:manage:orders"
    PARTNER_VIEW_ANALYTICS = "partner:view:analytics"
    PARTNER_MANAGE_PRODUCTS = "partner:manage:products"
    PARTNER_MANAGE_PRICING = "partner:manage:pricing"
    
    # CARD BDSFI Integration Permissions
    CARD_VIEW_MEMBERS = "card:view:members"
    CARD_UPDATE_MEMBERS = "card:update:members"
    CARD_MANAGE_LOANS = "card:manage:loans"
    CARD_VIEW_FINANCIALS = "card:view:financials"
    CARD_EXPORT_DATA = "card:export:data"
    
    # Mobile Operations Permissions
    MOBILE_FIELD_OPERATIONS = "mobile:field:operations"
    MOBILE_OFFLINE_SYNC = "mobile:offline:sync"
    MOBILE_GPS_TRACKING = "mobile:gps:tracking"
    MOBILE_PHOTO_UPLOAD = "mobile:photo:upload"
    
    # Administrative Permissions
    ADMIN_MANAGE_COOPERATIVES = "admin:manage:cooperatives"
    ADMIN_MANAGE_USERS = "admin:manage:users"
    ADMIN_VIEW_SYSTEM_LOGS = "admin:view:system:logs"
    ADMIN_MANAGE_PERMISSIONS = "admin:manage:permissions"
    ADMIN_SYSTEM_BACKUP = "admin:system:backup"

@dataclass
class AgriculturalRole:
    """Enhanced role definition with agricultural permissions"""
    name: str
    display_name: str
    description: str
    base_permissions: Set[str]
    agricultural_permissions: Set[AgriculturalPermission]
    organization_scope: str  # 'own', 'cooperative', 'region', 'all'
    data_access_level: str  # 'own', 'assigned', 'organization', 'all'
    
    def get_all_permissions(self) -> Set[str]:
        """Get all permissions (base + agricultural) as strings"""
        agri_perms = {perm.value for perm in self.agricultural_permissions}
        return self.base_permissions.union(agri_perms)

class AgriculturalRoleManager:
    """Manages agricultural roles and their permissions"""
    
    def __init__(self):
        self.roles = self._initialize_agricultural_roles()
    
    def _initialize_agricultural_roles(self) -> Dict[str, AgriculturalRole]:
        """Initialize all agricultural roles with their permissions"""
        
        roles = {}
        
        # Super Admin - Full system access
        roles['super_admin'] = AgriculturalRole(
            name='super_admin',
            display_name='Super Administrator',
            description='Full system access across all organizations and agricultural operations',
            base_permissions={
                'user:create', 'user:read', 'user:update', 'user:delete',
                'organization:create', 'organization:read', 'organization:update', 'organization:delete',
                'permission:manage', 'audit:view', 'system:admin'
            },
            agricultural_permissions=set(AgriculturalPermission),  # All permissions
            organization_scope='all',
            data_access_level='all'
        )
        
        # Admin - Organization-wide administrative access
        roles['admin'] = AgriculturalRole(
            name='admin',
            display_name='Administrator',
            description='Administrative access within organization and agricultural operations',
            base_permissions={
                'user:create', 'user:read', 'user:update',
                'organization:read', 'organization:update',
                'audit:view'
            },
            agricultural_permissions={
                # Farmer Management
                AgriculturalPermission.FARMER_VIEW_ALL,
                AgriculturalPermission.FARMER_CREATE,
                AgriculturalPermission.FARMER_UPDATE_ALL,
                AgriculturalPermission.FARMER_VERIFY,
                AgriculturalPermission.FARMER_EXPORT,
                
                # Farm Management
                AgriculturalPermission.FARM_VIEW_ALL,
                AgriculturalPermission.FARM_CREATE,
                AgriculturalPermission.FARM_UPDATE_ALL,
                AgriculturalPermission.FARM_EXPORT,
                
                # Activities and Analytics
                AgriculturalPermission.ACTIVITY_VIEW_ALL,
                AgriculturalPermission.ACTIVITY_APPROVE,
                AgriculturalPermission.ACTIVITY_EXPORT,
                AgriculturalPermission.ANALYTICS_VIEW_ADVANCED,
                AgriculturalPermission.ANALYTICS_VIEW_FINANCIAL,
                AgriculturalPermission.ANALYTICS_EXPORT,
                
                # Administrative
                AgriculturalPermission.ADMIN_MANAGE_COOPERATIVES,
                AgriculturalPermission.ADMIN_MANAGE_USERS,
                AgriculturalPermission.ADMIN_VIEW_SYSTEM_LOGS,
                
                # CARD BDSFI
                AgriculturalPermission.CARD_VIEW_MEMBERS,
                AgriculturalPermission.CARD_UPDATE_MEMBERS,
                AgriculturalPermission.CARD_VIEW_FINANCIALS,
                AgriculturalPermission.CARD_EXPORT_DATA
            },
            organization_scope='cooperative',
            data_access_level='organization'
        )
        
        # Manager - Operational management within organization
        roles['manager'] = AgriculturalRole(
            name='manager',
            display_name='Manager',
            description='Operational management of agricultural activities within organization',
            base_permissions={
                'user:read', 'user:update',
                'organization:read'
            },
            agricultural_permissions={
                # Farmer Management
                AgriculturalPermission.FARMER_VIEW_ALL,
                AgriculturalPermission.FARMER_CREATE,
                AgriculturalPermission.FARMER_UPDATE_ALL,
                AgriculturalPermission.FARMER_EXPORT,
                
                # Farm Management
                AgriculturalPermission.FARM_VIEW_ALL,
                AgriculturalPermission.FARM_CREATE,
                AgriculturalPermission.FARM_UPDATE_ALL,
                
                # Activities
                AgriculturalPermission.ACTIVITY_VIEW_ALL,
                AgriculturalPermission.ACTIVITY_CREATE,
                AgriculturalPermission.ACTIVITY_UPDATE_ALL,
                AgriculturalPermission.ACTIVITY_APPROVE,
                
                # Inputs and Transactions
                AgriculturalPermission.INPUT_VIEW_CATALOG,
                AgriculturalPermission.INPUT_VIEW_PRICING,
                AgriculturalPermission.INPUT_APPROVE_ORDERS,
                AgriculturalPermission.TRANSACTION_VIEW_ALL,
                AgriculturalPermission.TRANSACTION_APPROVE,
                
                # Analytics
                AgriculturalPermission.ANALYTICS_VIEW_ADVANCED,
                AgriculturalPermission.ANALYTICS_CREATE_REPORTS,
                
                # CARD BDSFI
                AgriculturalPermission.CARD_VIEW_MEMBERS,
                AgriculturalPermission.CARD_UPDATE_MEMBERS
            },
            organization_scope='cooperative',
            data_access_level='organization'
        )
        
        # Field Officer - Direct farmer support and field operations
        roles['field_officer'] = AgriculturalRole(
            name='field_officer',
            display_name='Field Officer',
            description='Agricultural extension services and direct farmer support',
            base_permissions={
                'user:read', 'user:update'
            },
            agricultural_permissions={
                # Farmer Management
                AgriculturalPermission.FARMER_VIEW_ALL,
                AgriculturalPermission.FARMER_CREATE,
                AgriculturalPermission.FARMER_UPDATE_ALL,
                
                # Farm Management
                AgriculturalPermission.FARM_VIEW_ALL,
                AgriculturalPermission.FARM_CREATE,
                AgriculturalPermission.FARM_UPDATE_ALL,
                
                # Field Operations
                AgriculturalPermission.FIELD_VIEW_ALL,
                AgriculturalPermission.FIELD_CREATE,
                AgriculturalPermission.FIELD_UPDATE_ALL,
                
                # Activities
                AgriculturalPermission.ACTIVITY_VIEW_ALL,
                AgriculturalPermission.ACTIVITY_CREATE,
                AgriculturalPermission.ACTIVITY_UPDATE_ALL,
                
                # Crops and Inputs
                AgriculturalPermission.CROP_VIEW,
                AgriculturalPermission.INPUT_VIEW_CATALOG,
                AgriculturalPermission.INPUT_VIEW_PRICING,
                
                # Harvest
                AgriculturalPermission.HARVEST_VIEW_ALL,
                AgriculturalPermission.HARVEST_CREATE,
                AgriculturalPermission.HARVEST_UPDATE_ALL,
                
                # Weather and Analytics
                AgriculturalPermission.WEATHER_VIEW,
                AgriculturalPermission.ANALYTICS_VIEW_BASIC,
                
                # Mobile Operations
                AgriculturalPermission.MOBILE_FIELD_OPERATIONS,
                AgriculturalPermission.MOBILE_OFFLINE_SYNC,
                AgriculturalPermission.MOBILE_GPS_TRACKING,
                AgriculturalPermission.MOBILE_PHOTO_UPLOAD,
                
                # CARD BDSFI
                AgriculturalPermission.CARD_VIEW_MEMBERS
            },
            organization_scope='cooperative',
            data_access_level='assigned'
        )
        
        # Farmer - Own farm operations and data
        roles['farmer'] = AgriculturalRole(
            name='farmer',
            display_name='Farmer',
            description='Access to own farm operations and agricultural data',
            base_permissions={
                'user:read:own', 'user:update:own'
            },
            agricultural_permissions={
                # Own Data Access
                AgriculturalPermission.FARMER_VIEW_OWN,
                AgriculturalPermission.FARMER_UPDATE_OWN,
                AgriculturalPermission.FARM_VIEW_OWN,
                AgriculturalPermission.FARM_UPDATE_OWN,
                AgriculturalPermission.FIELD_VIEW_OWN,
                AgriculturalPermission.FIELD_UPDATE_OWN,
                
                # Activities
                AgriculturalPermission.ACTIVITY_VIEW_OWN,
                AgriculturalPermission.ACTIVITY_CREATE,
                AgriculturalPermission.ACTIVITY_UPDATE_OWN,
                
                # Crops and Inputs
                AgriculturalPermission.CROP_VIEW,
                AgriculturalPermission.INPUT_VIEW_CATALOG,
                
                # Harvest
                AgriculturalPermission.HARVEST_VIEW_OWN,
                AgriculturalPermission.HARVEST_CREATE,
                AgriculturalPermission.HARVEST_UPDATE_OWN,
                
                # Transactions
                AgriculturalPermission.TRANSACTION_VIEW_OWN,
                AgriculturalPermission.TRANSACTION_CREATE,
                
                # Weather and Basic Analytics
                AgriculturalPermission.WEATHER_VIEW,
                AgriculturalPermission.ANALYTICS_VIEW_BASIC,
                
                # Mobile Operations
                AgriculturalPermission.MOBILE_FIELD_OPERATIONS,
                AgriculturalPermission.MOBILE_OFFLINE_SYNC,
                AgriculturalPermission.MOBILE_GPS_TRACKING,
                AgriculturalPermission.MOBILE_PHOTO_UPLOAD
            },
            organization_scope='own',
            data_access_level='own'
        )
        
        # Input Supplier - Partner role for agricultural input companies
        roles['input_supplier'] = AgriculturalRole(
            name='input_supplier',
            display_name='Input Supplier',
            description='Agricultural input supplier with product and order management',
            base_permissions={
                'partner:api:access'
            },
            agricultural_permissions={
                # Product Management
                AgriculturalPermission.INPUT_VIEW_CATALOG,
                AgriculturalPermission.INPUT_CREATE,
                AgriculturalPermission.INPUT_UPDATE,
                AgriculturalPermission.INPUT_MANAGE_STOCK,
                AgriculturalPermission.INPUT_MANAGE_PRICING,
                
                # Order Management
                AgriculturalPermission.TRANSACTION_VIEW_ALL,
                AgriculturalPermission.TRANSACTION_UPDATE,
                
                # Partner Operations
                AgriculturalPermission.PARTNER_VIEW_CATALOG,
                AgriculturalPermission.PARTNER_MANAGE_ORDERS,
                AgriculturalPermission.PARTNER_MANAGE_PRODUCTS,
                AgriculturalPermission.PARTNER_MANAGE_PRICING,
                AgriculturalPermission.PARTNER_VIEW_ANALYTICS
            },
            organization_scope='partner',
            data_access_level='partner'
        )
        
        # Logistics Partner - Transportation and delivery services
        roles['logistics_partner'] = AgriculturalRole(
            name='logistics_partner',
            display_name='Logistics Partner',
            description='Transportation and delivery services for agricultural operations',
            base_permissions={
                'partner:api:access'
            },
            agricultural_permissions={
                # Order and Delivery Management
                AgriculturalPermission.TRANSACTION_VIEW_ALL,
                AgriculturalPermission.TRANSACTION_UPDATE,
                
                # Location and Tracking
                AgriculturalPermission.FARM_VIEW_ALL,
                AgriculturalPermission.MOBILE_GPS_TRACKING,
                
                # Partner Operations
                AgriculturalPermission.PARTNER_MANAGE_ORDERS,
                AgriculturalPermission.PARTNER_VIEW_ANALYTICS
            },
            organization_scope='partner',
            data_access_level='partner'
        )
        
        # Financial Partner - Credit and financing services
        roles['financial_partner'] = AgriculturalRole(
            name='financial_partner',
            display_name='Financial Partner',
            description='Credit assessment and financing services for farmers',
            base_permissions={
                'partner:api:access'
            },
            agricultural_permissions={
                # Farmer Assessment
                AgriculturalPermission.FARMER_VIEW_ALL,
                AgriculturalPermission.FARM_VIEW_ALL,
                AgriculturalPermission.ACTIVITY_VIEW_ALL,
                AgriculturalPermission.HARVEST_VIEW_ALL,
                
                # Financial Operations
                AgriculturalPermission.TRANSACTION_VIEW_ALL,
                AgriculturalPermission.TRANSACTION_CREATE,
                AgriculturalPermission.TRANSACTION_APPROVE,
                AgriculturalPermission.ANALYTICS_VIEW_FINANCIAL,
                
                # CARD BDSFI Integration
                AgriculturalPermission.CARD_VIEW_MEMBERS,
                AgriculturalPermission.CARD_MANAGE_LOANS,
                AgriculturalPermission.CARD_VIEW_FINANCIALS
            },
            organization_scope='partner',
            data_access_level='partner'
        )
        
        # Buyer/Processor - Agricultural product purchasing
        roles['buyer_processor'] = AgriculturalRole(
            name='buyer_processor',
            display_name='Buyer/Processor',
            description='Agricultural product buyers and processors',
            base_permissions={
                'partner:api:access'
            },
            agricultural_permissions={
                # Product and Harvest Information
                AgriculturalPermission.CROP_VIEW,
                AgriculturalPermission.HARVEST_VIEW_ALL,
                AgriculturalPermission.FARM_VIEW_ALL,
                
                # Transaction Management
                AgriculturalPermission.TRANSACTION_VIEW_ALL,
                AgriculturalPermission.TRANSACTION_CREATE,
                
                # Partner Operations
                AgriculturalPermission.PARTNER_VIEW_CATALOG,
                AgriculturalPermission.PARTNER_PLACE_ORDERS,
                AgriculturalPermission.PARTNER_VIEW_ANALYTICS
            },
            organization_scope='partner',
            data_access_level='partner'
        )
        
        return roles
    
    def get_role(self, role_name: str) -> AgriculturalRole:
        """Get role by name"""
        return self.roles.get(role_name)
    
    def get_all_roles(self) -> Dict[str, AgriculturalRole]:
        """Get all roles"""
        return self.roles
    
    def get_permissions_for_role(self, role_name: str) -> Set[str]:
        """Get all permissions for a specific role"""
        role = self.get_role(role_name)
        return role.get_all_permissions() if role else set()
    
    def check_permission(self, role_name: str, permission: str) -> bool:
        """Check if a role has a specific permission"""
        role_permissions = self.get_permissions_for_role(role_name)
        return permission in role_permissions
    
    def get_agricultural_roles_by_tier(self) -> Dict[str, List[str]]:
        """Get roles organized by tier"""
        return {
            'administrative': ['super_admin', 'admin', 'manager'],
            'operational': ['field_officer', 'farmer'],
            'partners': ['input_supplier', 'logistics_partner', 'financial_partner', 'buyer_processor']
        }
    
    def export_role_permissions_matrix(self) -> Dict:
        """Export complete role-permission matrix for documentation"""
        matrix = {}
        
        for role_name, role in self.roles.items():
            matrix[role_name] = {
                'display_name': role.display_name,
                'description': role.description,
                'organization_scope': role.organization_scope,
                'data_access_level': role.data_access_level,
                'permissions': {
                    'base': list(role.base_permissions),
                    'agricultural': [perm.value for perm in role.agricultural_permissions],
                    'total_count': len(role.get_all_permissions())
                }
            }
        
        return matrix

# Global instance
agricultural_role_manager = AgriculturalRoleManager()

def get_agricultural_permissions_for_user(user_role: str) -> Set[str]:
    """Get agricultural permissions for a user role"""
    return agricultural_role_manager.get_permissions_for_role(user_role)

def check_agricultural_permission(user_role: str, permission: str) -> bool:
    """Check if user role has specific agricultural permission"""
    return agricultural_role_manager.check_permission(user_role, permission)

def get_role_matrix() -> Dict:
    """Get the complete role-permission matrix"""
    return agricultural_role_manager.export_role_permissions_matrix()
