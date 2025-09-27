"""
MAGSASA-CARD Enhanced Platform - Agricultural Data Models
Integrates comprehensive agricultural operations with the AgriTech Access Control System
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from src.models.user import db
import enum

# Agricultural-specific enums
class FarmType(enum.Enum):
    RICE = "rice"
    CORN = "corn"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    LIVESTOCK = "livestock"
    MIXED = "mixed"
    ORGANIC = "organic"

class CropStage(enum.Enum):
    PLANNING = "planning"
    PLANTED = "planted"
    GROWING = "growing"
    FLOWERING = "flowering"
    HARVESTING = "harvesting"
    HARVESTED = "harvested"
    FALLOW = "fallow"

class ActivityType(enum.Enum):
    PLANTING = "planting"
    FERTILIZING = "fertilizing"
    PESTICIDE = "pesticide"
    IRRIGATION = "irrigation"
    WEEDING = "weeding"
    HARVESTING = "harvesting"
    SOIL_PREP = "soil_preparation"
    MAINTENANCE = "maintenance"

class InputType(enum.Enum):
    FERTILIZER = "fertilizer"
    PESTICIDE = "pesticide"
    HERBICIDE = "herbicide"
    SEED = "seed"
    EQUIPMENT = "equipment"
    FUEL = "fuel"
    LABOR = "labor"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DELIVERED = "delivered"
    PAID = "paid"
    CANCELLED = "cancelled"

# Agricultural Organization Extensions
class AgriculturalOrganization(db.Model):
    """
    Extended organization model for agricultural cooperatives and regions
    """
    __tablename__ = 'agricultural_organizations'
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    
    # Agricultural-specific fields
    cooperative_code = Column(String(20), unique=True)
    region = Column(String(100))
    province = Column(String(100))
    municipality = Column(String(100))
    barangay = Column(String(100))
    
    # Agricultural focus
    primary_crops = Column(JSON)  # List of main crops
    farm_types = Column(JSON)    # List of farm types supported
    total_farmers = Column(Integer, default=0)
    total_hectares = Column(Float, default=0.0)
    
    # CARD BDSFI integration
    card_bdsfi_member = Column(Boolean, default=False)
    card_member_since = Column(Date)
    
    # Relationships
    organization = relationship("Organization", back_populates="agricultural_org")
    farmers = relationship("Farmer", back_populates="agricultural_org")
    farms = relationship("Farm", back_populates="agricultural_org")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Farmer Profile Management
class Farmer(db.Model):
    """
    Comprehensive farmer profile integrated with user management
    """
    __tablename__ = 'farmers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    agricultural_org_id = Column(Integer, ForeignKey('agricultural_organizations.id'))
    
    # RSBSA Integration (Registry System for Basic Sectors in Agriculture)
    rsbsa_id = Column(String(50), unique=True)
    farmer_id_card = Column(String(100))  # Physical ID card number
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    last_name = Column(String(100), nullable=False)
    suffix = Column(String(20))
    
    # Contact Information
    mobile_number = Column(String(20))
    email = Column(String(120))
    
    # Address Information
    region = Column(String(100))
    province = Column(String(100))
    municipality = Column(String(100))
    barangay = Column(String(100))
    purok_sitio = Column(String(100))
    zip_code = Column(String(10))
    
    # Agricultural Information
    farming_experience_years = Column(Integer)
    primary_occupation = Column(String(100))
    secondary_occupation = Column(String(100))
    
    # Financial Information
    annual_income = Column(Float)
    credit_score = Column(Float)  # AgScore integration
    card_bdsfi_member = Column(Boolean, default=False)
    card_member_id = Column(String(50))
    
    # Emergency Contact
    emergency_contact_name = Column(String(200))
    emergency_contact_number = Column(String(20))
    emergency_contact_relationship = Column(String(50))
    
    # System Fields
    is_active = Column(Boolean, default=True)
    verification_status = Column(String(20), default='pending')  # pending, verified, rejected
    
    # Relationships
    user = relationship("User", back_populates="farmer_profile")
    agricultural_org = relationship("AgriculturalOrganization", back_populates="farmers")
    farms = relationship("Farm", back_populates="farmer")
    activities = relationship("FarmActivity", back_populates="farmer")
    transactions = relationship("InputTransaction", back_populates="farmer")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Farm Management
class Farm(db.Model):
    """
    Individual farm properties with comprehensive management
    """
    __tablename__ = 'farms'
    
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    agricultural_org_id = Column(Integer, ForeignKey('agricultural_organizations.id'))
    
    # Farm Identification
    farm_name = Column(String(200))
    farm_code = Column(String(50), unique=True)
    
    # Location Information
    region = Column(String(100))
    province = Column(String(100))
    municipality = Column(String(100))
    barangay = Column(String(100))
    purok_sitio = Column(String(100))
    
    # Geographic Coordinates
    latitude = Column(Float)
    longitude = Column(Float)
    elevation = Column(Float)
    
    # Farm Details
    total_area_hectares = Column(Float, nullable=False)
    cultivated_area_hectares = Column(Float)
    farm_type = Column(Enum(FarmType), nullable=False)
    
    # Ownership Information
    ownership_type = Column(String(50))  # owned, rented, shared, etc.
    land_title_number = Column(String(100))
    
    # Soil and Climate Information
    soil_type = Column(String(100))
    water_source = Column(String(100))
    irrigation_type = Column(String(100))
    
    # Farm Infrastructure
    has_storage = Column(Boolean, default=False)
    has_drying_facility = Column(Boolean, default=False)
    has_machinery = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="farms")
    agricultural_org = relationship("AgriculturalOrganization", back_populates="farms")
    fields = relationship("Field", back_populates="farm")
    activities = relationship("FarmActivity", back_populates="farm")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Field Management
class Field(db.Model):
    """
    Individual field parcels within farms
    """
    __tablename__ = 'fields'
    
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False)
    
    # Field Identification
    field_name = Column(String(200), nullable=False)
    field_number = Column(String(20))
    
    # Field Details
    area_hectares = Column(Float, nullable=False)
    soil_type = Column(String(100))
    slope = Column(String(50))
    drainage = Column(String(50))
    
    # Current Crop Information
    current_crop_id = Column(Integer, ForeignKey('crops.id'))
    crop_stage = Column(Enum(CropStage), default=CropStage.FALLOW)
    planting_date = Column(Date)
    expected_harvest_date = Column(Date)
    
    # Field Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    farm = relationship("Farm", back_populates="fields")
    current_crop = relationship("Crop")
    activities = relationship("FarmActivity", back_populates="field")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Crop Management
class Crop(db.Model):
    """
    Crop varieties and management information
    """
    __tablename__ = 'crops'
    
    id = Column(Integer, primary_key=True)
    
    # Crop Identification
    crop_name = Column(String(200), nullable=False)
    variety = Column(String(200))
    crop_code = Column(String(50), unique=True)
    
    # Crop Classification
    crop_category = Column(String(100))  # cereal, vegetable, fruit, etc.
    crop_type = Column(Enum(FarmType))
    
    # Growing Information
    growing_season = Column(String(100))  # wet, dry, year-round
    maturity_days = Column(Integer)
    yield_per_hectare = Column(Float)  # Expected yield
    
    # Requirements
    water_requirement = Column(String(100))
    fertilizer_requirement = Column(JSON)  # Recommended fertilizer program
    pesticide_program = Column(JSON)      # Recommended pest management
    
    # Market Information
    market_price_per_kg = Column(Float)
    market_demand = Column(String(50))    # high, medium, low
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Farm Activity Tracking
class FarmActivity(db.Model):
    """
    Comprehensive farm activity and operation tracking
    """
    __tablename__ = 'farm_activities'
    
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False)
    field_id = Column(Integer, ForeignKey('fields.id'))
    
    # Activity Information
    activity_type = Column(Enum(ActivityType), nullable=False)
    activity_name = Column(String(200), nullable=False)
    activity_description = Column(Text)
    
    # Timing Information
    activity_date = Column(Date, nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # Resource Information
    labor_hours = Column(Float)
    labor_cost = Column(Float)
    material_cost = Column(Float)
    equipment_used = Column(String(200))
    
    # Input Usage
    inputs_used = Column(JSON)  # List of inputs with quantities
    
    # Results and Notes
    area_covered_hectares = Column(Float)
    weather_conditions = Column(String(200))
    results = Column(Text)
    notes = Column(Text)
    
    # Photo Documentation
    photos = Column(JSON)  # List of photo URLs
    
    # GPS Tracking
    gps_coordinates = Column(JSON)  # GPS track if available
    
    # Relationships
    farmer = relationship("Farmer", back_populates="activities")
    farm = relationship("Farm", back_populates="activities")
    field = relationship("Field", back_populates="activities")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Agricultural Input Management
class AgriculturalInput(db.Model):
    """
    Agricultural inputs catalog (fertilizers, pesticides, seeds, etc.)
    """
    __tablename__ = 'agricultural_inputs'
    
    id = Column(Integer, primary_key=True)
    
    # Product Information
    product_name = Column(String(200), nullable=False)
    brand = Column(String(100))
    product_code = Column(String(50), unique=True)
    
    # Classification
    input_type = Column(Enum(InputType), nullable=False)
    category = Column(String(100))
    subcategory = Column(String(100))
    
    # Product Details
    description = Column(Text)
    active_ingredient = Column(String(200))
    concentration = Column(String(100))
    
    # Packaging Information
    package_size = Column(String(100))  # 50kg, 1L, etc.
    unit_of_measure = Column(String(20))  # kg, L, pcs, etc.
    
    # Pricing Information
    cost_price = Column(Float)
    selling_price = Column(Float)
    commission_rate = Column(Float)  # For CARD BDSFI commission model
    
    # Supplier Information
    supplier_name = Column(String(200))
    supplier_contact = Column(String(200))
    
    # Usage Information
    application_rate = Column(String(200))
    application_method = Column(String(200))
    crop_suitability = Column(JSON)  # List of suitable crops
    
    # Regulatory Information
    registration_number = Column(String(100))
    expiry_date = Column(Date)
    safety_instructions = Column(Text)
    
    # Inventory
    stock_quantity = Column(Integer, default=0)
    reorder_level = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Input Transactions (CARD BDSFI Integration)
class InputTransaction(db.Model):
    """
    Agricultural input transactions with CARD BDSFI auto-debit integration
    """
    __tablename__ = 'input_transactions'
    
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    
    # Transaction Information
    transaction_code = Column(String(50), unique=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    
    # Order Details
    items = Column(JSON, nullable=False)  # List of items with quantities and prices
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    
    # Payment Information
    payment_method = Column(String(50))  # card_auto_debit, cash, etc.
    payment_status = Column(String(20), default='pending')
    payment_date = Column(DateTime)
    
    # CARD BDSFI Integration
    card_member_id = Column(String(50))
    auto_debit_reference = Column(String(100))
    commission_amount = Column(Float)  # Commission for AgSense.ai
    
    # Delivery Information
    delivery_address = Column(Text)
    delivery_date = Column(Date)
    delivery_status = Column(String(20), default='pending')
    
    # Transaction Status
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Notes and References
    notes = Column(Text)
    reference_number = Column(String(100))
    
    # Relationships
    farmer = relationship("Farmer", back_populates="transactions")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Harvest and Production Tracking
class HarvestRecord(db.Model):
    """
    Harvest and production tracking for yield analysis
    """
    __tablename__ = 'harvest_records'
    
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False)
    field_id = Column(Integer, ForeignKey('fields.id'))
    crop_id = Column(Integer, ForeignKey('crops.id'), nullable=False)
    
    # Harvest Information
    harvest_date = Column(Date, nullable=False)
    area_harvested_hectares = Column(Float, nullable=False)
    
    # Production Data
    total_yield_kg = Column(Float, nullable=False)
    yield_per_hectare = Column(Float)  # Calculated field
    quality_grade = Column(String(50))
    moisture_content = Column(Float)
    
    # Market Information
    selling_price_per_kg = Column(Float)
    buyer_name = Column(String(200))
    total_revenue = Column(Float)
    
    # Cost Analysis
    total_production_cost = Column(Float)
    net_income = Column(Float)  # Calculated field
    profit_margin = Column(Float)  # Calculated field
    
    # Quality Assessment
    pest_damage_percentage = Column(Float, default=0.0)
    disease_damage_percentage = Column(Float, default=0.0)
    weather_damage_percentage = Column(Float, default=0.0)
    
    # Storage and Processing
    post_harvest_handling = Column(String(200))
    storage_location = Column(String(200))
    processing_method = Column(String(200))
    
    # Documentation
    photos = Column(JSON)  # Harvest photos
    certificates = Column(JSON)  # Quality certificates
    
    # Relationships
    farmer = relationship("Farmer")
    farm = relationship("Farm")
    field = relationship("Field")
    crop = relationship("Crop")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Agricultural Analytics and Insights
class FarmAnalytics(db.Model):
    """
    Aggregated analytics and insights for farms and farmers
    """
    __tablename__ = 'farm_analytics'
    
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey('farmers.id'))
    farm_id = Column(Integer, ForeignKey('farms.id'))
    agricultural_org_id = Column(Integer, ForeignKey('agricultural_organizations.id'))
    
    # Time Period
    analytics_period = Column(String(20))  # monthly, quarterly, yearly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Production Analytics
    total_area_planted = Column(Float, default=0.0)
    total_area_harvested = Column(Float, default=0.0)
    total_production_kg = Column(Float, default=0.0)
    average_yield_per_hectare = Column(Float, default=0.0)
    
    # Financial Analytics
    total_revenue = Column(Float, default=0.0)
    total_costs = Column(Float, default=0.0)
    net_income = Column(Float, default=0.0)
    profit_margin = Column(Float, default=0.0)
    
    # Input Usage Analytics
    fertilizer_usage_kg = Column(Float, default=0.0)
    pesticide_usage_l = Column(Float, default=0.0)
    seed_usage_kg = Column(Float, default=0.0)
    input_cost_per_hectare = Column(Float, default=0.0)
    
    # Efficiency Metrics
    labor_hours_per_hectare = Column(Float, default=0.0)
    cost_per_kg_produced = Column(Float, default=0.0)
    revenue_per_hectare = Column(Float, default=0.0)
    
    # Risk Assessment (AgScore Integration)
    risk_score = Column(Float)  # 0-100 scale
    risk_factors = Column(JSON)  # List of identified risk factors
    recommendations = Column(JSON)  # AI-generated recommendations
    
    # Sustainability Metrics
    water_usage_efficiency = Column(Float)
    soil_health_score = Column(Float)
    biodiversity_index = Column(Float)
    carbon_footprint = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Weather and Environmental Data
class WeatherData(db.Model):
    """
    Weather and environmental data for agricultural decision making
    """
    __tablename__ = 'weather_data'
    
    id = Column(Integer, primary_key=True)
    
    # Location Information
    region = Column(String(100), nullable=False)
    province = Column(String(100), nullable=False)
    municipality = Column(String(100), nullable=False)
    
    # Weather Station Information
    station_id = Column(String(50))
    station_name = Column(String(200))
    
    # Date and Time
    observation_date = Column(Date, nullable=False)
    observation_time = Column(DateTime)
    
    # Weather Parameters
    temperature_max = Column(Float)
    temperature_min = Column(Float)
    temperature_avg = Column(Float)
    humidity = Column(Float)
    rainfall_mm = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(String(20))
    
    # Agricultural Indices
    heat_index = Column(Float)
    growing_degree_days = Column(Float)
    evapotranspiration = Column(Float)
    
    # Data Source
    data_source = Column(String(100))  # PAGASA, satellite, etc.
    data_quality = Column(String(20))   # excellent, good, fair, poor
    
    created_at = Column(DateTime, default=datetime.utcnow)

# Add relationships to existing User model
def enhance_user_model():
    """
    Enhance the existing User model with agricultural relationships
    """
    # This would be added to the existing User model
    # user.farmer_profile = relationship("Farmer", back_populates="user", uselist=False)
    pass

# Add relationships to existing Organization model  
def enhance_organization_model():
    """
    Enhance the existing Organization model with agricultural relationships
    """
    # This would be added to the existing Organization model
    # organization.agricultural_org = relationship("AgriculturalOrganization", back_populates="organization", uselist=False)
    pass
