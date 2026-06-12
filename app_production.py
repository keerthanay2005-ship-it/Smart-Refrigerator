from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import os
from ml_engine import MLEngine

app = Flask(__name__)
app.secret_key = 'production-secret-key-change-in-production'
CORS(app)

# Database configuration
DATABASE = 'smart_fridge.db'

# ML Engine
ml_engine = MLEngine(DATABASE)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# User Management
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, household, preferences)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['username'],
            data['email'],
            hashed_password,
            data.get('household', ''),
            json.dumps(data.get('preferences', {}))
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({"message": "User registered successfully", "user_id": user_id})
    
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email or username already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE email = ?',
        (data['email'],)
    ).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], data['password']):
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        return jsonify({
            "token": "production-token",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email']
            }
        })
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Smart Dashboard
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    
    # Get user's items
    items = conn.execute('''
        SELECT * FROM food_items 
        WHERE user_id = ? 
        ORDER BY priority_score DESC
    ''', (user_id,)).fetchall()
    
    # Calculate metrics
    total_items = len(items)
    expiring_soon = len([item for item in items if item['days_left'] <= 3])
    low_stock = len([item for item in items if item['quantity'] <= 2])
    expired = len([item for item in items if item['days_left'] < 0])
    
    # Get category distribution
    categories = {}
    for item in items:
        cat = item['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    conn.close()
    
    return jsonify({
        "total_items": total_items,
        "expiring_soon": expiring_soon,
        "low_stock": low_stock,
        "expired": expired,
        "items": [dict(item) for item in items[:10]],
        "categories": categories
    })

# Food Inventory Management
@app.route('/add', methods=['POST'])
def add_food():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    
    # Calculate expiry information
    if data.get('expiry'):
        expiry_date = datetime.strptime(data['expiry'], "%Y-%m-%d")
        days_left = (expiry_date - datetime.today()).days
    else:
        # Use estimated freshness
        estimated_days = int(data.get('estimated_freshness', 7))
        expiry_date = datetime.today() + timedelta(days=estimated_days)
        days_left = estimated_days
    
    # Calculate priority score
    priority_score = calculate_priority_score({
        'days_left': days_left,
        'quantity': data.get('quantity', 1),
        'usage_frequency': 0
    })
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO food_items (
                user_id, name, category, quantity, quantity_unit,
                storage_location, expiry_date, has_expiry, days_left,
                priority_score, freshness_status, usage_frequency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data['name'],
            data['category'],
            float(data['quantity']),
            data.get('quantity_unit', 'pieces'),
            data.get('storage_location', 'Shelf'),
            expiry_date.strftime('%Y-%m-%d'),
            data.get('has_expiry', True),
            days_left,
            priority_score,
            'Unknown',
            0
        ))
        
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Item Added",
            "item_id": item_id,
            "priority_score": priority_score
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/items')
def get_items():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    items = conn.execute('''
        SELECT * FROM food_items 
        WHERE user_id = ? 
        ORDER BY priority_score DESC
    ''', (user_id,)).fetchall()
    conn.close()
    
    # Update risk indicators
    result_items = []
    for item in items:
        item_dict = dict(item)
        item_dict['expiry_risk'] = get_expiry_risk(item['days_left'])
        item_dict['freshness_color'] = get_freshness_color(item['days_left'])
        result_items.append(item_dict)
    
    return jsonify(result_items)

@app.route('/update/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    
    # Calculate new expiry info if changed
    update_data = {
        'name': data['name'],
        'category': data['category'],
        'quantity': float(data['quantity']),
        'quantity_unit': data.get('quantity_unit', 'pieces'),
        'storage_location': data.get('storage_location', 'Shelf'),
        'updated_at': datetime.now()
    }
    
    if 'expiry' in data:
        expiry_date = datetime.strptime(data['expiry'], "%Y-%m-%d")
        days_left = (expiry_date - datetime.today()).days
        update_data['expiry_date'] = expiry_date.strftime('%Y-%m-%d')
        update_data['days_left'] = days_left
        update_data['priority_score'] = calculate_priority_score({
            'days_left': days_left,
            'quantity': data['quantity'],
            'usage_frequency': 0
        })
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build dynamic UPDATE query
        set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values()) + [user_id, item_id]
        
        cursor.execute(f'''
            UPDATE food_items 
            SET {set_clause}
            WHERE user_id = ? AND id = ?
        ''', values)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Item updated"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM food_items 
            WHERE user_id = ? AND id = ?
        ''', (user_id, item_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Deleted"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ML Features
@app.route('/predict-consumption', methods=['POST'])
def predict_consumption():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get current items
    conn = get_db_connection()
    items = conn.execute('''
        SELECT * FROM food_items 
        WHERE user_id = ? AND days_left >= 0
    ''', (user_id,)).fetchall()
    conn.close()
    
    # Convert to list of dicts
    current_items = [dict(item) for item in items]
    
    # Get ML predictions
    predictions = ml_engine.predict_consumption(user_id, current_items)
    
    return jsonify({"predictions": predictions})

@app.route('/train-models', methods=['POST'])
def train_models():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Train ML models for this user
    success = ml_engine.train_models(user_id)
    
    if success:
        return jsonify({"message": "Models trained successfully"})
    else:
        return jsonify({"error": "Insufficient data for training"}), 400

@app.route('/analytics')
def analytics():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get clustering analysis
    clusters = ml_engine.perform_clustering(user_id)
    
    # Get consumption trends
    conn = get_db_connection()
    
    # Monthly trends (last 6 months)
    monthly_trends = conn.execute('''
        SELECT 
            strftime('%m', consumed_date) as month,
            COUNT(*) as consumed,
            SUM(CASE WHEN consumption_reason = 'thrown_away' THEN 1 ELSE 0 END) as wasted
        FROM consumption_history 
        WHERE user_id = ? 
        AND consumed_date >= date('now', '-6 months')
        GROUP BY strftime('%m', consumed_date)
        ORDER BY month
    ''', (user_id,)).fetchall()
    
    # Category distribution
    category_dist = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM food_items 
        WHERE user_id = ? AND days_left >= 0
        GROUP BY category
    ''', (user_id,)).fetchall()
    
    # Calculate waste rate
    total_consumed = conn.execute('''
        SELECT COUNT(*) FROM consumption_history 
        WHERE user_id = ? AND consumed_date >= date('now', '-30 days')
    ''', (user_id,)).fetchone()[0]
    
    total_wasted = conn.execute('''
        SELECT COUNT(*) FROM consumption_history 
        WHERE user_id = ? AND consumption_reason = 'thrown_away'
        AND consumed_date >= date('now', '-30 days')
    ''', (user_id,)).fetchone()[0]
    
    waste_rate = (total_wasted / max(total_consumed, 1)) * 100
    sustainability_score = max(0, 100 - waste_rate)
    
    conn.close()
    
    return jsonify({
        "clusters": clusters,
        "monthly_trends": [dict(row) for row in monthly_trends],
        "category_distribution": dict(row for row in category_dist),
        "waste_rate": waste_rate,
        "sustainability_score": sustainability_score
    })

@app.route('/risk-heatmap')
def risk_heatmap():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    items = conn.execute('''
        SELECT category, days_left 
        FROM food_items 
        WHERE user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    
    # Calculate risk by category
    categories = ['Fruits', 'Vegetables', 'Dairy', 'Packaged', 'Meat', 'Other']
    risk_grid = []
    
    for category in categories:
        category_items = [item for item in items if item['category'] == category]
        
        if category_items:
            avg_risk = np.mean([get_risk_score(item['days_left']) for item in category_items])
            risk_level = get_risk_level(avg_risk)
            
            risk_grid.append({
                "category": category,
                "risk_level": risk_level,
                "risk_score": avg_risk,
                "item_count": len(category_items),
                "color": get_risk_color(avg_risk)
            })
    
    return jsonify({"risk_grid": risk_grid})

# Freshness Detection (mock for now)
@app.route('/detect-freshness', methods=['POST'])
def detect_freshness():
    # In production, this would use real computer vision
    return jsonify({
        "freshness": "Fresh",
        "confidence": 0.85,
        "color_analysis": {
            "mean_hue": 45,
            "mean_saturation": 120,
            "mean_value": 180
        }
    })

# Helper Functions
def calculate_priority_score(item):
    days_left = item.get('days_left', 0)
    quantity = item.get('quantity', 1)
    usage_freq = item.get('usage_frequency', 1)
    
    if days_left < 0:
        return 100
    elif days_left <= 3:
        return 80 + (3 - days_left) * 10
    elif days_left <= 7:
        return 50 + (7 - days_left) * 6
    else:
        return max(10, 50 - days_left / 2)

def get_expiry_risk(days_left):
    if days_left < 0:
        return "Expired"
    elif days_left <= 2:
        return "Critical"
    elif days_left <= 5:
        return "High"
    elif days_left <= 10:
        return "Medium"
    else:
        return "Low"

def get_freshness_color(days_left):
    if days_left < 0:
        return "#FF0000"
    elif days_left <= 3:
        return "#FF6B6B"
    elif days_left <= 7:
        return "#FFA500"
    elif days_left <= 14:
        return "#FFD700"
    else:
        return "#90EE90"

def get_risk_score(days_left):
    if days_left < 0:
        return 100
    elif days_left <= 3:
        return 80
    elif days_left <= 7:
        return 60
    elif days_left <= 14:
        return 40
    else:
        return 20

def get_risk_level(score):
    if score >= 80:
        return "High"
    elif score >= 50:
        return "Medium"
    else:
        return "Low"

def get_risk_color(score):
    if score >= 80:
        return "#FF0000"
    elif score >= 50:
        return "#FFA500"
    else:
        return "#90EE90"

@app.route('/api/alerts')
def get_alerts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM food_items WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    expired = []
    expiring_soon = []
    low_stock = []
    
    for item in items:
        item_dict = dict(item)
        days_left = item_dict.get('days_left', 0)
        quantity = float(item_dict.get('quantity', 1))
        unit = item_dict.get('quantity_unit', 'pieces')
        
        # Check expired
        if days_left < 0:
            expired.append(item_dict)
        # Check expiring soon (0 to 3 days)
        elif 0 <= days_left <= 3:
            expiring_soon.append(item_dict)
            
        # Check low stock
        is_low = False
        if unit in ['pieces', 'dozen'] and quantity <= 2:
            is_low = True
        elif unit in ['kg', 'lb', 'liters'] and quantity <= 0.5:
            is_low = True
        elif unit in ['g', 'ml', 'oz'] and quantity <= 200:
            is_low = True
            
        if is_low:
            low_stock.append(item_dict)
            
    return jsonify({
        "expired": expired,
        "expiring_soon": expiring_soon,
        "low_stock": low_stock
    })

if __name__ == '__main__':
    print("🚀 Starting Smart Fridge AI Production Server...")
    print("📊 Database: SQLite")
    print("🤖 ML Engine: Real Machine Learning")
    print("🌐 Open: http://localhost:5000")
    app.run(debug=True, port=5000)
