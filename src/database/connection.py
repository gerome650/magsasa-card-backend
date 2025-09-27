import sqlite3
import os

def get_db_connection():
    """Get database connection with proper configuration"""
    db_path = os.path.join(os.path.dirname(__file__), 'magsasa_dynamic_pricing.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn

def execute_query(query, params=None):
    """Execute a query and return results"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()
