#!/usr/bin/env python3
"""
Smart Fridge AI - Production Setup Script
Run this to set up the production database and ML system
"""

import os
import sys
import subprocess
from database_setup import setup_database
from ml_engine import MLEngine

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python version OK: {sys.version}")
    return True

def install_dependencies():
    """Install required packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_production.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = ['models', 'static', 'templates']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"✅ Directory exists: {directory}")

def copy_static_files():
    """Copy static files to correct locations"""
    import shutil
    
    # Copy templates
    if os.path.exists('templates/index.html'):
        print("✅ Templates already in place")
    else:
        print("⚠️  Make sure templates/index.html exists")
    
    # Copy static files
    static_files = ['style.css', 'script.js']
    for file in static_files:
        src = f'static/{file}'
        if os.path.exists(src):
            print(f"✅ Static file ready: {file}")
        else:
            print(f"⚠️  Missing static file: {file}")

def test_database():
    """Test database connection"""
    try:
        import sqlite3
        conn = sqlite3.connect('smart_fridge.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        table_names = [table[0] for table in tables]
        expected_tables = ['users', 'food_items', 'consumption_history', 'shopping_predictions']
        
        if all(table in table_names for table in expected_tables):
            print("✅ Database tables ready")
            return True
        else:
            print("❌ Missing database tables")
            return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_ml_engine():
    """Test ML engine functionality"""
    try:
        ml_engine = MLEngine()
        print("✅ ML Engine initialized")
        return True
    except Exception as e:
        print(f"❌ ML Engine error: {e}")
        return False

def main():
    """Main setup function"""
    print("Smart Fridge AI - Production Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup directories
    setup_directories()
    
    # Setup database
    print("\n📊 Setting up database...")
    setup_database()
    
    # Test database
    if not test_database():
        return False
    
    # Test ML engine
    if not test_ml_engine():
        return False
    
    # Check static files
    copy_static_files()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Run: python app_production.py")
    print("2. Open: http://localhost:5000")
    print("3. Register a new user")
    print("4. Add some food items")
    print("5. Train ML models: POST /train-models")
    print("6. Get predictions: POST /predict-consumption")
    
    print("\n🔥 Production features enabled:")
    print("✅ SQLite database with persistent storage")
    print("✅ Real ML models (KNN, Naïve Bayes, Decision Tree, Random Forest)")
    print("✅ User authentication and sessions")
    print("✅ Data relationships and constraints")
    print("✅ Scalable architecture")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
