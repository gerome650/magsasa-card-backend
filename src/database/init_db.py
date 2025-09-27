import sqlite3
import os
from .connection import get_db_connection

def ensure_database():
    """Initialize database with tables and sample data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create agricultural_inputs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agricultural_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                base_price REAL NOT NULL,
                unit TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create pricing_tiers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing_tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_id INTEGER,
                min_quantity INTEGER NOT NULL,
                max_quantity INTEGER,
                discount_percentage REAL NOT NULL,
                FOREIGN KEY (input_id) REFERENCES agricultural_inputs (id)
            )
        ''')
        
        # Create logistics_options table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logistics_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_cost REAL NOT NULL,
                cost_per_km REAL NOT NULL,
                estimated_days INTEGER NOT NULL,
                description TEXT
            )
        ''')
        
        # Insert sample data if tables are empty
        cursor.execute('SELECT COUNT(*) FROM agricultural_inputs')
        if cursor.fetchone()[0] == 0:
            insert_sample_data(cursor)
        
        conn.commit()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        conn.close()

def insert_sample_data(cursor):
    """Insert sample agricultural inputs and pricing data"""
    
    # Sample agricultural inputs
    inputs_data = [
        ('Organic Fertilizer', 'Fertilizer', 1200.00, 'kg', 'High-quality organic fertilizer for sustainable farming'),
        ('Hybrid Rice Seeds', 'Seeds', 85.00, 'kg', 'High-yield hybrid rice variety suitable for tropical climate'),
        ('Pesticide Spray', 'Pesticide', 450.00, 'liter', 'Effective pest control solution for various crops'),
        ('NPK Fertilizer', 'Fertilizer', 950.00, 'kg', 'Balanced nitrogen, phosphorus, and potassium fertilizer'),
        ('Corn Seeds', 'Seeds', 120.00, 'kg', 'Premium corn seeds with high germination rate')
    ]
    
    cursor.executemany('''
        INSERT INTO agricultural_inputs (name, category, base_price, unit, description)
        VALUES (?, ?, ?, ?, ?)
    ''', inputs_data)
    
    # Sample pricing tiers
    pricing_tiers_data = [
        (1, 1, 50, 5.0),      # Organic Fertilizer: 1-50kg, 5% discount
        (1, 51, 100, 10.0),   # Organic Fertilizer: 51-100kg, 10% discount
        (1, 101, None, 15.0), # Organic Fertilizer: 101+kg, 15% discount
        (2, 1, 25, 3.0),      # Rice Seeds: 1-25kg, 3% discount
        (2, 26, 50, 8.0),     # Rice Seeds: 26-50kg, 8% discount
        (3, 1, 10, 2.0),      # Pesticide: 1-10L, 2% discount
        (3, 11, 25, 7.0),     # Pesticide: 11-25L, 7% discount
        (4, 1, 100, 6.0),     # NPK Fertilizer: 1-100kg, 6% discount
        (4, 101, None, 12.0), # NPK Fertilizer: 101+kg, 12% discount
        (5, 1, 20, 4.0),      # Corn Seeds: 1-20kg, 4% discount
    ]
    
    cursor.executemany('''
        INSERT INTO pricing_tiers (input_id, min_quantity, max_quantity, discount_percentage)
        VALUES (?, ?, ?, ?)
    ''', pricing_tiers_data)
    
    # Sample logistics options
    logistics_data = [
        ('Standard Delivery', 150.00, 8.50, 5, 'Regular delivery service within 5 business days'),
        ('Express Delivery', 300.00, 15.00, 2, 'Fast delivery service within 2 business days'),
        ('Bulk Transport', 500.00, 5.00, 7, 'Cost-effective option for large orders'),
        ('Same Day Delivery', 450.00, 25.00, 1, 'Premium same-day delivery for urgent orders')
    ]
    
    cursor.executemany('''
        INSERT INTO logistics_options (name, base_cost, cost_per_km, estimated_days, description)
        VALUES (?, ?, ?, ?, ?)
    ''', logistics_data)
