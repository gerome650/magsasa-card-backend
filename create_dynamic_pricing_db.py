#!/usr/bin/env python3
"""
Create New Database with Dynamic Pricing Structure
MAGSASA-CARD Enhanced Platform
"""

import sqlite3
import os
from datetime import datetime, date

def create_dynamic_pricing_database():
    """Create a new SQLite database with dynamic pricing structure"""
    print("🌾 Creating MAGSASA-CARD Dynamic Pricing Database...")
    
    # Ensure database directory exists
    os.makedirs('src/database', exist_ok=True)
    
    # Create database connection
    db_path = 'src/database/dynamic_pricing.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("📊 Creating dynamic pricing tables...")
    
    # Create AgriculturalInput table with dynamic pricing
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agricultural_inputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        category VARCHAR(100),
        brand VARCHAR(100),
        description TEXT,
        active_ingredient VARCHAR(200),
        concentration VARCHAR(100),
        package_size VARCHAR(100),
        unit_of_measure VARCHAR(20),
        
        -- Dynamic Pricing Structure
        wholesale_price REAL NOT NULL,
        retail_price REAL NOT NULL,
        market_retail_price REAL,
        platform_margin REAL,
        margin_percentage REAL,
        
        -- Bulk Pricing
        bulk_tier_1_quantity INTEGER,
        bulk_tier_1_price REAL,
        bulk_tier_2_quantity INTEGER,
        bulk_tier_2_price REAL,
        bulk_tier_3_quantity INTEGER,
        bulk_tier_3_price REAL,
        
        -- Logistics Options
        supplier_delivery_available BOOLEAN DEFAULT 0,
        supplier_delivery_fee REAL DEFAULT 0.0,
        supplier_delivery_radius_km REAL,
        supplier_delivery_minimum_order REAL,
        supplier_delivery_days INTEGER,
        
        platform_logistics_available BOOLEAN DEFAULT 1,
        platform_logistics_base_fee REAL DEFAULT 0.0,
        platform_logistics_per_km_rate REAL DEFAULT 0.0,
        platform_logistics_minimum_order REAL,
        platform_logistics_days INTEGER,
        
        farmer_pickup_available BOOLEAN DEFAULT 1,
        pickup_location_address TEXT,
        pickup_discount_percentage REAL DEFAULT 0.0,
        
        -- Product Details
        supplier_name VARCHAR(200),
        application_rate VARCHAR(200),
        application_method VARCHAR(200),
        crop_suitability TEXT, -- JSON string
        current_stock INTEGER DEFAULT 0,
        reorder_level INTEGER DEFAULT 10,
        
        -- System Fields
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create LogisticsOption table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logistics_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_name VARCHAR(200) NOT NULL,
        provider_type VARCHAR(50) NOT NULL,
        service_regions TEXT, -- JSON string
        service_radius_km REAL,
        base_delivery_fee REAL DEFAULT 0.0,
        per_km_rate REAL DEFAULT 0.0,
        minimum_order_value REAL DEFAULT 0.0,
        free_delivery_threshold REAL,
        standard_delivery_days INTEGER DEFAULT 3,
        express_delivery_days INTEGER DEFAULT 1,
        express_delivery_surcharge REAL DEFAULT 0.0,
        operating_days TEXT, -- JSON string
        operating_hours VARCHAR(100),
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create InputPricingHistory table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS input_pricing_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_id INTEGER NOT NULL,
        wholesale_price REAL NOT NULL,
        retail_price REAL NOT NULL,
        platform_margin REAL NOT NULL,
        margin_percentage REAL NOT NULL,
        change_reason VARCHAR(200),
        effective_from TIMESTAMP NOT NULL,
        effective_to TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (input_id) REFERENCES agricultural_inputs (id)
    )
    ''')
    
    # Create InputTransaction table with dynamic pricing
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS input_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER,
        transaction_code VARCHAR(50) UNIQUE NOT NULL,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Order Details
        items TEXT NOT NULL, -- JSON string
        
        -- Pricing Breakdown
        subtotal_wholesale REAL NOT NULL,
        subtotal_retail REAL NOT NULL,
        platform_margin_total REAL NOT NULL,
        
        -- Additional Costs
        delivery_fee REAL DEFAULT 0.0,
        logistics_provider_fee REAL DEFAULT 0.0,
        platform_logistics_margin REAL DEFAULT 0.0,
        
        -- Discounts and Taxes
        tax_amount REAL DEFAULT 0.0,
        discount_amount REAL DEFAULT 0.0,
        bulk_discount_amount REAL DEFAULT 0.0,
        pickup_discount_amount REAL DEFAULT 0.0,
        
        -- Final Totals
        total_amount REAL NOT NULL,
        total_platform_revenue REAL NOT NULL,
        
        -- Delivery Information
        delivery_type VARCHAR(50) NOT NULL,
        delivery_address TEXT,
        delivery_date DATE,
        delivery_status VARCHAR(20) DEFAULT 'pending',
        logistics_option_id INTEGER,
        
        -- Payment Information
        payment_method VARCHAR(50),
        payment_status VARCHAR(20) DEFAULT 'pending',
        payment_date TIMESTAMP,
        
        -- CARD BDSFI Integration
        card_member_id VARCHAR(50),
        auto_debit_reference VARCHAR(100),
        card_member_discount REAL DEFAULT 0.0,
        
        -- Status
        status VARCHAR(20) DEFAULT 'pending',
        notes TEXT,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (logistics_option_id) REFERENCES logistics_options (id)
    )
    ''')
    
    # Create PricingAnalytics table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pricing_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_date DATE NOT NULL,
        period_type VARCHAR(20),
        input_id INTEGER,
        category VARCHAR(100),
        
        -- Pricing Metrics
        avg_wholesale_price REAL,
        avg_retail_price REAL,
        avg_platform_margin REAL,
        avg_margin_percentage REAL,
        
        -- Volume Metrics
        total_quantity_sold REAL,
        total_transactions INTEGER,
        total_revenue REAL,
        total_platform_revenue REAL,
        
        -- Market Comparison
        market_price_comparison REAL,
        competitor_price_data TEXT, -- JSON string
        
        -- Logistics Metrics
        avg_delivery_fee REAL,
        delivery_type_breakdown TEXT, -- JSON string
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (input_id) REFERENCES agricultural_inputs (id)
    )
    ''')
    
    print("📦 Inserting sample data with dynamic pricing...")
    
    # Insert sample logistics options
    logistics_data = [
        ("CARD MRI Logistics", "platform_logistics", '["Laguna", "Batangas", "Quezon"]', 50.0, 100.0, 5.0, 500.0, 2000.0, 2, 1, 150.0, '["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]', "8:00-17:00", 1),
        ("Supplier Direct Delivery", "supplier_delivery", '["Laguna", "Rizal"]', 30.0, 50.0, 3.0, 1000.0, 3000.0, 1, 1, 0.0, '["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]', "9:00-16:00", 1),
        ("Farmer Pickup - CARD Center", "farmer_pickup", '["Laguna"]', 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0, '["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]', "8:00-17:00", 1)
    ]
    
    cursor.executemany('''
    INSERT INTO logistics_options (
        provider_name, provider_type, service_regions, service_radius_km,
        base_delivery_fee, per_km_rate, minimum_order_value, free_delivery_threshold,
        standard_delivery_days, express_delivery_days, express_delivery_surcharge,
        operating_days, operating_hours, is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', logistics_data)
    
    # Insert sample agricultural inputs with dynamic pricing
    inputs_data = [
        (
            "Complete Fertilizer 14-14-14", "fertilizer", "Atlas", 
            "Complete fertilizer suitable for rice and corn",
            "NPK", "14-14-14", "50kg", "kg",
            # Dynamic Pricing
            850.0, 950.0, 1100.0, 100.0, 11.76,
            # Bulk Pricing
            10, 920.0, 25, 900.0, 50, 880.0,
            # Logistics
            1, 75.0, 25.0, 1500.0, 1,
            1, 100.0, 5.0, 500.0, 2,
            1, "CARD MRI Center, Laguna", 2.0,
            # Product Details
            "Atlas Fertilizer Corporation", "2-3 bags per hectare", "Broadcasting",
            '["rice", "corn", "vegetables"]', 500, 50, 1
        ),
        (
            "Urea 46-0-0", "fertilizer", "Planters",
            "High nitrogen fertilizer for top dressing",
            "Urea", "46-0-0", "50kg", "kg",
            # Dynamic Pricing
            1200.0, 1350.0, 1500.0, 150.0, 12.5,
            # Bulk Pricing
            10, 1320.0, 25, 1300.0, 50, 1280.0,
            # Logistics
            1, 80.0, 30.0, 2000.0, 2,
            1, 100.0, 5.0, 500.0, 2,
            1, "CARD MRI Center, Laguna", 3.0,
            # Product Details
            "Planters Products Inc.", "1-2 bags per hectare", "Side dressing",
            '["rice", "corn", "sugarcane"]', 300, 30, 1
        ),
        (
            "Hybrid Rice Seeds - PSB Rc82", "seeds", "PhilRice",
            "High-yielding hybrid rice variety",
            "Hybrid Seeds", "PSB Rc82", "20kg", "kg",
            # Dynamic Pricing
            180.0, 200.0, 250.0, 20.0, 11.11,
            # Bulk Pricing
            5, 195.0, 10, 190.0, 20, 185.0,
            # Logistics
            0, 0.0, 0.0, 0.0, 0,
            1, 50.0, 3.0, 200.0, 1,
            1, "CARD MRI Center, Laguna", 5.0,
            # Product Details
            "Philippine Rice Research Institute", "120-140 kg per hectare", "Direct seeding or transplanting",
            '["rice"]', 100, 20, 1
        )
    ]
    
    cursor.executemany('''
    INSERT INTO agricultural_inputs (
        name, category, brand, description, active_ingredient, concentration, package_size, unit_of_measure,
        wholesale_price, retail_price, market_retail_price, platform_margin, margin_percentage,
        bulk_tier_1_quantity, bulk_tier_1_price, bulk_tier_2_quantity, bulk_tier_2_price, bulk_tier_3_quantity, bulk_tier_3_price,
        supplier_delivery_available, supplier_delivery_fee, supplier_delivery_radius_km, supplier_delivery_minimum_order, supplier_delivery_days,
        platform_logistics_available, platform_logistics_base_fee, platform_logistics_per_km_rate, platform_logistics_minimum_order, platform_logistics_days,
        farmer_pickup_available, pickup_location_address, pickup_discount_percentage,
        supplier_name, application_rate, application_method, crop_suitability, current_stock, reorder_level, is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', inputs_data)
    
    # Insert pricing history
    cursor.execute('''
    INSERT INTO input_pricing_history (input_id, wholesale_price, retail_price, platform_margin, margin_percentage, change_reason, effective_from)
    SELECT id, wholesale_price, retail_price, platform_margin, margin_percentage, 'initial_pricing', datetime('now')
    FROM agricultural_inputs
    ''')
    
    # Insert sample analytics
    today = date.today().isoformat()
    cursor.execute('''
    INSERT INTO pricing_analytics (
        analysis_date, period_type, input_id, category,
        avg_wholesale_price, avg_retail_price, avg_platform_margin, avg_margin_percentage,
        total_quantity_sold, total_transactions, total_revenue, total_platform_revenue,
        market_price_comparison, avg_delivery_fee, delivery_type_breakdown
    )
    SELECT 
        ?, 'daily', id, category,
        wholesale_price, retail_price, platform_margin, margin_percentage,
        0.0, 0, 0.0, 0.0,
        ((market_retail_price - retail_price) / market_retail_price) * 100,
        75.0, '{"supplier_delivery": 40, "platform_logistics": 45, "farmer_pickup": 15}'
    FROM agricultural_inputs
    ''', (today,))
    
    conn.commit()
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM agricultural_inputs")
    input_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM logistics_options")
    logistics_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM input_pricing_history")
    history_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pricing_analytics")
    analytics_count = cursor.fetchone()[0]
    
    print(f"\n🎉 Dynamic Pricing Database Created Successfully!")
    print(f"📊 Database Summary:")
    print(f"   • Database: {db_path}")
    print(f"   • Agricultural Inputs: {input_count}")
    print(f"   • Logistics Options: {logistics_count}")
    print(f"   • Pricing History Records: {history_count}")
    print(f"   • Analytics Records: {analytics_count}")
    
    # Show sample pricing
    cursor.execute('''
    SELECT name, wholesale_price, retail_price, market_retail_price, platform_margin, margin_percentage
    FROM agricultural_inputs LIMIT 2
    ''')
    
    print(f"\n💰 Sample Pricing Structure:")
    for row in cursor.fetchall():
        name, wholesale, retail, market, margin, margin_pct = row
        savings = market - retail
        savings_pct = (savings / market) * 100
        print(f"   • {name}:")
        print(f"     - Wholesale: ₱{wholesale:,.2f}")
        print(f"     - Farmer Price: ₱{retail:,.2f}")
        print(f"     - Market Price: ₱{market:,.2f}")
        print(f"     - Platform Margin: ₱{margin:,.2f} ({margin_pct:.1f}%)")
        print(f"     - Farmer Savings: ₱{savings:,.2f} ({savings_pct:.1f}%)")
    
    # Show logistics options
    cursor.execute('SELECT provider_name, provider_type, base_delivery_fee, free_delivery_threshold, standard_delivery_days FROM logistics_options')
    
    print(f"\n🚚 Logistics Options Available:")
    for row in cursor.fetchall():
        name, type_, base_fee, free_threshold, days = row
        print(f"   • {name} ({type_})")
        print(f"     - Base Fee: ₱{base_fee:,.2f}")
        if free_threshold:
            print(f"     - Free Delivery: ₱{free_threshold:,.2f}+")
        print(f"     - Delivery Time: {days} days")
    
    conn.close()
    print(f"\n✅ Database ready for use!")

if __name__ == "__main__":
    create_dynamic_pricing_database()
