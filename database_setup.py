import sqlite3
import os
from datetime import datetime

def setup_database():
    """Create SQLite database with proper schema"""
    
    # Remove existing database if it exists
    if os.path.exists('smart_fridge.db'):
        os.remove('smart_fridge.db')
    
    # Create connection
    conn = sqlite3.connect('smart_fridge.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            household VARCHAR(100),
            preferences TEXT,  -- JSON string for preferences
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create food_items table
    cursor.execute('''
        CREATE TABLE food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            quantity DECIMAL(10,2) NOT NULL,
            quantity_unit VARCHAR(20) DEFAULT 'pieces',
            storage_location VARCHAR(20) DEFAULT 'Shelf',
            expiry_date DATE,
            has_expiry BOOLEAN DEFAULT 1,
            days_left INTEGER,
            priority_score INTEGER DEFAULT 0,
            freshness_status VARCHAR(20) DEFAULT 'Unknown',
            usage_frequency INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create consumption_history table
    cursor.execute('''
        CREATE TABLE consumption_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER,
            item_name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            quantity_consumed DECIMAL(10,2) NOT NULL,
            quantity_unit VARCHAR(20) DEFAULT 'pieces',
            consumed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            days_before_expiry INTEGER,
            consumption_reason VARCHAR(50),  -- 'eaten', 'expired', 'thrown_away'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create shopping_predictions table
    cursor.execute('''
        CREATE TABLE shopping_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            predicted_next_purchase DATE,
            confidence_score DECIMAL(3,2),
            avg_days_between_purchases INTEGER,
            seasonal_factor DECIMAL(3,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX idx_food_items_user_id ON food_items(user_id)')
    cursor.execute('CREATE INDEX idx_food_items_expiry ON food_items(expiry_date)')
    cursor.execute('CREATE INDEX idx_consumption_user_date ON consumption_history(user_id, consumed_date)')
    cursor.execute('CREATE INDEX idx_predictions_user ON shopping_predictions(user_id)')
    
    # Insert sample data
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, household)
        VALUES (?, ?, ?, ?)
    ''', ('demo_user', 'demo@example.com', 'hashed_password', 'Demo Household'))
    
    conn.commit()
    conn.close()
    print("✅ Database setup complete!")
    print("📁 Database file: smart_fridge.db")
    print("👥 Sample user created: demo_user / demo@example.com")

if __name__ == '__main__':
    setup_database()
