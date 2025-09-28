#!/usr/bin/env python3
"""
Deployment Verification Script for KaAni Integration
Ensures all required files and dependencies are present for successful deployment
"""

import os
import sys
import subprocess

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status"""
    if os.path.isdir(dirpath):
        files = len([f for f in os.listdir(dirpath) if f.endswith('.py')])
        print(f"✅ {description}: {dirpath} ({files} Python files)")
        return True
    else:
        print(f"❌ {description}: {dirpath} - NOT FOUND")
        return False

def check_git_tracking(filepath):
    """Check if a file is tracked by git"""
    try:
        result = subprocess.run(['git', 'ls-files', filepath], 
                              capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print(f"✅ Git tracking: {filepath}")
            return True
        else:
            print(f"❌ Git tracking: {filepath} - NOT TRACKED")
            return False
    except subprocess.CalledProcessError:
        print(f"❌ Git tracking: {filepath} - ERROR CHECKING")
        return False

def check_import(module_name, description):
    """Check if a module can be imported"""
    try:
        __import__(module_name)
        print(f"✅ Import test: {description}")
        return True
    except ImportError as e:
        print(f"❌ Import test: {description} - {str(e)}")
        return False

def main():
    """Run deployment verification checks"""
    print("🔍 KaAni Deployment Verification")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 0
    
    # Core application files
    print("\n📁 Core Application Files:")
    total_checks += 1
    if check_file_exists("app.py", "Main application file"):
        checks_passed += 1
    
    total_checks += 1
    if check_file_exists("requirements.txt", "Dependencies file"):
        checks_passed += 1
    
    total_checks += 1
    if check_file_exists("Procfile", "Deployment configuration"):
        checks_passed += 1
    
    # KaAni integration files
    print("\n🤖 KaAni Integration Files:")
    kaani_files = [
        ("src/kaani_integration/__init__.py", "KaAni module init"),
        ("src/kaani_integration/openai_provider.py", "OpenAI provider"),
        ("src/kaani_integration/agscore_calculator.py", "AgScore calculator"),
        ("src/kaani_integration/diagnosis_engine.py", "Diagnosis engine"),
        ("src/routes/kaani_routes.py", "KaAni API routes")
    ]
    
    for filepath, description in kaani_files:
        total_checks += 1
        if check_file_exists(filepath, description):
            checks_passed += 1
    
    # Directory structure
    print("\n📂 Directory Structure:")
    directories = [
        ("src/kaani_integration", "KaAni integration module"),
        ("src/routes", "API routes directory"),
        ("src/database", "Database directory")
    ]
    
    for dirpath, description in directories:
        total_checks += 1
        if check_directory_exists(dirpath, description):
            checks_passed += 1
    
    # Git tracking verification
    print("\n📋 Git Tracking Status:")
    git_files = [
        "app.py",
        "requirements.txt",
        "src/kaani_integration/__init__.py",
        "src/kaani_integration/openai_provider.py",
        "src/kaani_integration/agscore_calculator.py", 
        "src/kaani_integration/diagnosis_engine.py",
        "src/routes/kaani_routes.py"
    ]
    
    for filepath in git_files:
        total_checks += 1
        if check_git_tracking(filepath):
            checks_passed += 1
    
    # Import tests
    print("\n🔧 Import Tests:")
    import_tests = [
        ("flask", "Flask framework"),
        ("openai", "OpenAI library"),
        ("src.routes.kaani_routes", "KaAni routes"),
        ("src.kaani_integration.openai_provider", "OpenAI provider"),
        ("src.kaani_integration.diagnosis_engine", "Diagnosis engine")
    ]
    
    for module, description in import_tests:
        total_checks += 1
        if check_import(module, description):
            checks_passed += 1
    
    # App configuration check
    print("\n⚙️ Application Configuration:")
    try:
        import app
        flask_app = app.create_app()
        
        # Check version
        total_checks += 1
        with flask_app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                data = response.get_json()
                if data and data.get('version') == '2.1.0':
                    print("✅ App version: 2.1.0 (KaAni enabled)")
                    checks_passed += 1
                else:
                    print(f"❌ App version: {data.get('version') if data else 'Unknown'} (Expected 2.1.0)")
            else:
                print(f"❌ App response: HTTP {response.status_code}")
        
        # Check KaAni blueprint registration
        total_checks += 1
        blueprint_names = [bp.name for bp in flask_app.blueprints.values()]
        if 'kaani' in blueprint_names:
            print("✅ KaAni blueprint: Registered successfully")
            checks_passed += 1
        else:
            print(f"❌ KaAni blueprint: Not registered (Available: {blueprint_names})")
            
    except Exception as e:
        print(f"❌ App configuration test failed: {str(e)}")
        total_checks += 2  # Account for both checks above
    
    # Final results
    print("\n" + "=" * 50)
    print(f"🎯 Verification Results: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("✅ ALL CHECKS PASSED - Ready for deployment!")
        print("🚀 KaAni integration is properly configured")
        return True
    else:
        print("❌ Some checks failed - Fix required before deployment")
        print("🔧 Review the failed items above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
