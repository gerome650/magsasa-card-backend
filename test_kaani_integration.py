#!/usr/bin/env python3
"""
Test script to verify KaAni integration is working properly
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all KaAni-related imports"""
    try:
        print("Testing KaAni integration imports...")
        
        # Test KaAni routes import
        from src.routes.kaani_routes import kaani_bp
        print("✅ KaAni routes imported successfully")
        
        # Test KaAni integration modules
        from src.kaani_integration.openai_provider import OpenAIProvider
        print("✅ OpenAI provider imported successfully")
        
        from src.kaani_integration.agscore_calculator import AgScoreCalculator
        print("✅ AgScore calculator imported successfully")
        
        from src.kaani_integration.diagnosis_engine import DiagnosisEngine
        print("✅ Diagnosis engine imported successfully")
        
        # Test main app import
        import app
        print("✅ Main app imported successfully")
        
        # Test app creation
        flask_app = app.create_app()
        print("✅ Flask app created successfully")
        
        # Check if KaAni blueprint is registered
        blueprint_names = [bp.name for bp in flask_app.blueprints.values()]
        if 'kaani' in blueprint_names:
            print("✅ KaAni blueprint registered successfully")
        else:
            print("❌ KaAni blueprint NOT registered")
            print(f"Available blueprints: {blueprint_names}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_routes():
    """Test KaAni route registration"""
    try:
        print("\nTesting KaAni route registration...")
        
        import app
        flask_app = app.create_app()
        
        # Get all registered routes
        routes = []
        for rule in flask_app.url_map.iter_rules():
            routes.append(str(rule))
        
        # Check for KaAni routes
        kaani_routes = [route for route in routes if 'kaani' in route.lower()]
        
        if kaani_routes:
            print(f"✅ Found {len(kaani_routes)} KaAni routes:")
            for route in kaani_routes[:5]:  # Show first 5
                print(f"   - {route}")
            if len(kaani_routes) > 5:
                print(f"   ... and {len(kaani_routes) - 5} more")
        else:
            print("❌ No KaAni routes found")
            print("Available routes:")
            for route in routes[:10]:  # Show first 10 routes
                print(f"   - {route}")
        
        return len(kaani_routes) > 0
        
    except Exception as e:
        print(f"❌ Route testing error: {str(e)}")
        return False

def test_database():
    """Test database connection and KaAni tables"""
    try:
        print("\nTesting database and KaAni tables...")
        
        import sqlite3
        
        # Connect to database
        conn = sqlite3.connect('src/database/dynamic_pricing.db')
        cursor = conn.cursor()
        
        # Check for KaAni tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%farmer%' OR name LIKE '%diagnosis%' OR name LIKE '%agscore%'")
        kaani_tables = cursor.fetchall()
        
        if kaani_tables:
            print(f"✅ Found {len(kaani_tables)} KaAni-related tables:")
            for table in kaani_tables:
                print(f"   - {table[0]}")
        else:
            print("❌ No KaAni tables found")
        
        conn.close()
        return len(kaani_tables) > 0
        
    except Exception as e:
        print(f"❌ Database testing error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 KaAni Integration Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test imports
    if test_imports():
        tests_passed += 1
    
    # Test routes
    if test_routes():
        tests_passed += 1
    
    # Test database
    if test_database():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All KaAni integration tests PASSED!")
        print("🚀 Ready for deployment!")
        return True
    else:
        print("❌ Some KaAni integration tests FAILED!")
        print("🔧 Fix required before deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
