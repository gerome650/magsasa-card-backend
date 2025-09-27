#!/usr/bin/env python3
"""
Enhanced Agricultural Models with Dynamic Pricing Structure
MAGSASA-CARD Enhanced Platform
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .user import db

# Enums for better data integrity
class TransactionStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class DeliveryType(enum.Enum):
    SUPPLIER_DELIVERY = "supplier_delivery"
    PLATFORM_LOGISTICS = "platform_logistics"
    FARMER_PICKUP = "farmer_pickup"

class PricingTier(enum.Enum):
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    PREMIUM = "premium"
    BULK_DISCOUNT = "bulk_discount"

# Enhanced Agricultural Input Model with Dynamic Pricing
class AgriculturalInput(db.Model):
    """
    Enhanced agricultural input model with dynamic pricing structure
    Supports wholesale-retail spreads and flexible logistics options
    """
    __tablename__ = 'agricultural_inputs'
    
    id = Column(Integer, primary_key=True)
    
    # Basic Product Information
    name = Column(String(200), nullable=False)
    category = Column(String(100))  # fertilizer, pesticide, seed, etc.
    brand = Column(String(100))
    description = Column(Text)
    
    # Technical Specifications
    active_ingredient = Column(String(200))
    concentration = Column(String(100))
    
    # Packaging Information
    package_size = Column(String(100))  # 50kg, 1L, etc.
    unit_of_measure = Column(String(20))  # kg, L, pcs, etc.
    
    # DYNAMIC PRICING STRUCTURE
    # Wholesale Pricing (AgSense negotiated prices)
    wholesale_price = Column(Float, nullable=False)  # AgSense negotiated wholesale price
    wholesale_minimum_quantity = Column(Integer, default=1)
    wholesale_supplier_id = Column(Integer, ForeignKey('organizations.id'))
    
    # Retail Pricing (Farmer prices)
    retail_price = Column(Float, nullable=False)  # Price farmers pay
    market_retail_price = Column(Float)  # Standard market retail price for comparison
    
    # Dynamic Margin Calculation
    platform_margin = Column(Float)  # Calculated: retail_price - wholesale_price
    margin_percentage = Column(Float)  # Calculated: (platform_margin / wholesale_price) * 100
    
    # Bulk Pricing Tiers
    bulk_tier_1_quantity = Column(Integer)  # e.g., 10+ units
    bulk_tier_1_price = Column(Float)
    bulk_tier_2_quantity = Column(Integer)  # e.g., 50+ units
    bulk_tier_2_price = Column(Float)
    bulk_tier_3_quantity = Column(Integer)  # e.g., 100+ units
    bulk_tier_3_price = Column(Float)
    
    # LOGISTICS OPTIONS
    # Supplier Delivery Options
    supplier_delivery_available = Column(Boolean, default=False)
    supplier_delivery_fee = Column(Float, default=0.0)
    supplier_delivery_radius_km = Column(Float)  # Maximum delivery distance
    supplier_delivery_minimum_order = Column(Float)  # Minimum order for free delivery
    supplier_delivery_days = Column(Integer)  # Estimated delivery days
    
    # Platform Logistics Options
    platform_logistics_available = Column(Boolean, default=True)
    platform_logistics_base_fee = Column(Float, default=0.0)
    platform_logistics_per_km_rate = Column(Float, default=0.0)
    platform_logistics_minimum_order = Column(Float)  # Minimum order for logistics
    platform_logistics_days = Column(Integer)  # Estimated delivery days
    
    # Farmer Pickup Options
    farmer_pickup_available = Column(Boolean, default=True)
    pickup_location_address = Column(Text)
    pickup_location_coordinates = Column(String(100))  # GPS coordinates
    pickup_discount_percentage = Column(Float, default=0.0)  # Discount for pickup
    
    # Supplier Information
    supplier_name = Column(String(200))
    supplier_contact = Column(String(200))
    supplier_organization_id = Column(Integer, ForeignKey('organizations.id'))
    
    # Usage Information
    application_rate = Column(String(200))
    application_method = Column(String(200))
    crop_suitability = Column(JSON)  # List of suitable crops
    
    # Inventory Management
    current_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=10)
    max_stock_level = Column(Integer, default=1000)
    
    # Quality and Compliance
    expiry_date = Column(Date)
    batch_number = Column(String(100))
    quality_certification = Column(JSON)  # List of certifications
    
    # System Fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier_organization = relationship("Organization", foreign_keys=[supplier_organization_id])
    wholesale_supplier = relationship("Organization", foreign_keys=[wholesale_supplier_id])
    transactions = relationship("InputTransaction", back_populates="input_items")
    pricing_history = relationship("InputPricingHistory", back_populates="input_item")

# Input Pricing History for tracking price changes
class InputPricingHistory(db.Model):
    """
    Track pricing changes over time for transparency and analytics
    """
    __tablename__ = 'input_pricing_history'
    
    id = Column(Integer, primary_key=True)
    input_id = Column(Integer, ForeignKey('agricultural_inputs.id'), nullable=False)
    
    # Historical Pricing
    wholesale_price = Column(Float, nullable=False)
    retail_price = Column(Float, nullable=False)
    platform_margin = Column(Float, nullable=False)
    margin_percentage = Column(Float, nullable=False)
    
    # Change Information
    change_reason = Column(String(200))  # supplier_negotiation, market_adjustment, etc.
    changed_by_user_id = Column(Integer, ForeignKey('users.id'))
    
    # Effective Period
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime)
    
    # System Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    input_item = relationship("AgriculturalInput", back_populates="pricing_history")
    changed_by = relationship("User")

# Enhanced Logistics Options Model
class LogisticsOption(db.Model):
    """
    Flexible logistics options for input delivery
    """
    __tablename__ = 'logistics_options'
    
    id = Column(Integer, primary_key=True)
    
    # Provider Information
    provider_name = Column(String(200), nullable=False)
    provider_type = Column(Enum(DeliveryType), nullable=False)
    provider_organization_id = Column(Integer, ForeignKey('organizations.id'))
    
    # Service Area
    service_regions = Column(JSON)  # List of regions served
    service_radius_km = Column(Float)  # Maximum service radius
    
    # Pricing Structure
    base_delivery_fee = Column(Float, default=0.0)
    per_km_rate = Column(Float, default=0.0)
    per_kg_rate = Column(Float, default=0.0)
    minimum_order_value = Column(Float, default=0.0)
    free_delivery_threshold = Column(Float)  # Order value for free delivery
    
    # Service Levels
    standard_delivery_days = Column(Integer, default=3)
    express_delivery_days = Column(Integer, default=1)
    express_delivery_surcharge = Column(Float, default=0.0)
    
    # Capacity and Constraints
    max_weight_kg = Column(Float)
    max_volume_m3 = Column(Float)
    special_handling_available = Column(Boolean, default=False)
    special_handling_fee = Column(Float, default=0.0)
    
    # Operating Schedule
    operating_days = Column(JSON)  # List of operating days
    operating_hours = Column(String(100))  # e.g., "8:00-17:00"
    
    # System Fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    provider_organization = relationship("Organization")
    deliveries = relationship("DeliveryOrder", back_populates="logistics_option")

# Enhanced Input Transaction Model with Dynamic Pricing
class InputTransaction(db.Model):
    """
    Enhanced input transactions with dynamic pricing and flexible logistics
    """
    __tablename__ = 'input_transactions'
    
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    
    # Transaction Information
    transaction_code = Column(String(50), unique=True, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    
    # Order Details with Dynamic Pricing
    items = Column(JSON, nullable=False)  # List of items with dynamic pricing breakdown
    
    # Pricing Breakdown
    subtotal_wholesale = Column(Float, nullable=False)  # Total wholesale cost
    subtotal_retail = Column(Float, nullable=False)  # Total retail price to farmer
    platform_margin_total = Column(Float, nullable=False)  # Total platform margin
    
    # Additional Costs
    delivery_fee = Column(Float, default=0.0)
    logistics_provider_fee = Column(Float, default=0.0)  # Fee to logistics partner
    platform_logistics_margin = Column(Float, default=0.0)  # Platform margin on logistics
    
    # Taxes and Discounts
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    bulk_discount_amount = Column(Float, default=0.0)
    pickup_discount_amount = Column(Float, default=0.0)
    
    # Final Totals
    total_amount = Column(Float, nullable=False)  # Amount farmer pays
    total_platform_revenue = Column(Float, nullable=False)  # Platform total revenue
    
    # Delivery Information
    delivery_type = Column(Enum(DeliveryType), nullable=False)
    delivery_address = Column(Text)
    delivery_coordinates = Column(String(100))
    delivery_date = Column(Date)
    delivery_status = Column(String(20), default='pending')
    logistics_option_id = Column(Integer, ForeignKey('logistics_options.id'))
    
    # Payment Information
    payment_method = Column(String(50))  # card_auto_debit, cash, etc.
    payment_status = Column(String(20), default='pending')
    payment_date = Column(DateTime)
    
    # CARD BDSFI Integration
    card_member_id = Column(String(50))
    auto_debit_reference = Column(String(100))
    card_member_discount = Column(Float, default=0.0)  # Special CARD member discounts
    
    # Transaction Status
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Notes and References
    notes = Column(Text)
    reference_number = Column(String(100))
    
    # System Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="input_transactions")
    logistics_option = relationship("LogisticsOption")
    delivery_order = relationship("DeliveryOrder", back_populates="transaction", uselist=False)

# Delivery Order Tracking
class DeliveryOrder(db.Model):
    """
    Detailed delivery order tracking with real-time updates
    """
    __tablename__ = 'delivery_orders'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('input_transactions.id'), nullable=False)
    logistics_option_id = Column(Integer, ForeignKey('logistics_options.id'), nullable=False)
    
    # Delivery Details
    delivery_code = Column(String(50), unique=True, nullable=False)
    pickup_address = Column(Text, nullable=False)
    delivery_address = Column(Text, nullable=False)
    
    # Scheduling
    scheduled_pickup_date = Column(DateTime)
    scheduled_delivery_date = Column(DateTime)
    actual_pickup_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    
    # Tracking Information
    current_status = Column(String(50), default='pending')
    current_location = Column(String(200))
    current_coordinates = Column(String(100))
    estimated_arrival = Column(DateTime)
    
    # Delivery Personnel
    driver_name = Column(String(200))
    driver_contact = Column(String(50))
    vehicle_info = Column(String(200))
    
    # Delivery Confirmation
    delivered_to_name = Column(String(200))
    delivery_signature = Column(Text)  # Base64 encoded signature
    delivery_photo = Column(Text)  # Base64 encoded photo or file path
    delivery_notes = Column(Text)
    
    # System Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transaction = relationship("InputTransaction", back_populates="delivery_order")
    logistics_option = relationship("LogisticsOption", back_populates="deliveries")
    tracking_updates = relationship("DeliveryTracking", back_populates="delivery_order")

# Real-time Delivery Tracking
class DeliveryTracking(db.Model):
    """
    Real-time delivery tracking updates
    """
    __tablename__ = 'delivery_tracking'
    
    id = Column(Integer, primary_key=True)
    delivery_order_id = Column(Integer, ForeignKey('delivery_orders.id'), nullable=False)
    
    # Tracking Information
    status = Column(String(50), nullable=False)
    location = Column(String(200))
    coordinates = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Update Details
    description = Column(Text)
    updated_by = Column(String(200))  # Driver, system, admin, etc.
    
    # System Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    delivery_order = relationship("DeliveryOrder", back_populates="tracking_updates")

# Pricing Analytics Model
class PricingAnalytics(db.Model):
    """
    Analytics for pricing optimization and market insights
    """
    __tablename__ = 'pricing_analytics'
    
    id = Column(Integer, primary_key=True)
    
    # Time Period
    analysis_date = Column(Date, nullable=False)
    period_type = Column(String(20))  # daily, weekly, monthly
    
    # Product Analytics
    input_id = Column(Integer, ForeignKey('agricultural_inputs.id'))
    category = Column(String(100))
    
    # Pricing Metrics
    avg_wholesale_price = Column(Float)
    avg_retail_price = Column(Float)
    avg_platform_margin = Column(Float)
    avg_margin_percentage = Column(Float)
    
    # Volume Metrics
    total_quantity_sold = Column(Float)
    total_transactions = Column(Integer)
    total_revenue = Column(Float)
    total_platform_revenue = Column(Float)
    
    # Market Comparison
    market_price_comparison = Column(Float)  # % difference from market price
    competitor_price_data = Column(JSON)
    
    # Logistics Metrics
    avg_delivery_fee = Column(Float)
    delivery_type_breakdown = Column(JSON)  # Percentage by delivery type
    
    # System Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    input_item = relationship("AgriculturalInput")

# Add relationships to existing models
# These would be added to the existing Farmer model
"""
# Add to Farmer model:
input_transactions = relationship("InputTransaction", back_populates="farmer")
"""
