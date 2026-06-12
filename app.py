from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Setup absolute paths for templates and static folders to avoid TemplateNotFound errors
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# ---------------------------------------------------------
# Dynamic Backend Detection & Conditional Imports
# ---------------------------------------------------------
DB_BACKEND = os.getenv('DB_BACKEND', 'mock').lower()

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://drzoyuxfvzxkstrrjxes.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_YBu9s8jf7R-4y3K4mQ57CQ_jfFqQ2Zu')

# SQLite setup
try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False

# MongoDB setup
try:
    from flask_pymongo import PyMongo
    from bson.objectid import ObjectId
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

# ML setup
try:
    import numpy as np
    import pandas as pd
    from sklearn.cluster import KMeans
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.naive_bayes import GaussianNB
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.preprocessing import StandardScaler
    HAS_ML = True
except ImportError:
    HAS_ML = False

# Computer Vision setup
try:
    import cv2
    from PIL import Image
    import io
    import base64
    HAS_CV = True
except ImportError:
    HAS_CV = False

# ML Engine setup (for SQLite mode)
try:
    from ml_engine import MLEngine
    HAS_ML_ENGINE = True
except ImportError:
    HAS_ML_ENGINE = False

# Resolve backend conflicts / missing dependencies
if DB_BACKEND == 'mongodb' and not HAS_PYMONGO:
    print("[WARNING] MongoDB requested but flask_pymongo not installed. Falling back to Mock.")
    DB_BACKEND = 'mock'
elif DB_BACKEND == 'sqlite' and not HAS_SQLITE:
    print("[WARNING] SQLite requested but sqlite3 not available. Falling back to Mock.")
    DB_BACKEND = 'mock'
elif DB_BACKEND == 'supabase' and (not SUPABASE_URL or not SUPABASE_KEY):
    print("[WARNING] Supabase requested but URL or Key not set. Falling back to Mock.")
    DB_BACKEND = 'mock'

print(f"Active Smart Fridge Backend Database: {DB_BACKEND.upper()}")

# Supabase REST Helpers
def get_supabase_items(user_id):
    url = f"{SUPABASE_URL}/rest/v1/food_items?user_id=eq.{user_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            items = res.json()
            for item in items:
                item['expiry'] = item.get('expiry_date')
                item['id'] = str(item.get('id'))
            return items
        else:
            print(f"Supabase GET error: {res.status_code} {res.text}")
            return []
    except Exception as e:
        print(f"Supabase connection exception: {e}")
        return []

def add_supabase_item(user_id, item_data):
    url = f"{SUPABASE_URL}/rest/v1/food_items"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    payload = {
        "user_id": str(user_id),
        "name": item_data['name'],
        "category": item_data['category'],
        "quantity": float(item_data['quantity']),
        "quantity_unit": item_data.get('quantity_unit', 'pieces'),
        "storage_location": item_data.get('storage_location', 'Shelf'),
        "expiry_date": item_data['expiry'],
        "days_left": int(item_data['days_left']),
        "priority_score": int(item_data['priority_score']),
        "has_expiry": True
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            ret = res.json()[0]
            ret['id'] = str(ret.get('id'))
            return ret
        else:
            print(f"Supabase POST error: {res.status_code} {res.text}")
            return None
    except Exception as e:
        print(f"Supabase insert exception: {e}")
        return None

def update_supabase_item(user_id, item_id, item_data):
    url = f"{SUPABASE_URL}/rest/v1/food_items?id=eq.{item_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": item_data['name'],
        "category": item_data['category'],
        "quantity": float(item_data['quantity']),
        "quantity_unit": item_data.get('quantity_unit', 'pieces'),
        "storage_location": item_data.get('storage_location', 'Shelf'),
        "expiry_date": item_data['expiry'],
        "days_left": int(item_data['days_left']),
        "priority_score": int(item_data['priority_score'])
    }
    try:
        res = requests.patch(url, headers=headers, json=payload)
        return res.status_code in [200, 204]
    except Exception as e:
        print(f"Supabase update exception: {e}")
        return False

def delete_supabase_item(user_id, item_id):
    url = f"{SUPABASE_URL}/rest/v1/food_items?id=eq.{item_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.delete(url, headers=headers)
        return res.status_code in [200, 204]
    except Exception as e:
        print(f"Supabase delete exception: {e}")
        return False

# Supabase Users & Notifications Helpers
def register_supabase_user(username, email, password_hash, household):
    check_url = f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{email}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(check_url, headers=headers)
        if res.status_code == 200 and len(res.json()) > 0:
            return {"error": "Email already exists"}
            
        insert_url = f"{SUPABASE_URL}/rest/v1/profiles"
        post_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        payload = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "household": household,
            "preferences": "{}"
        }
        res_post = requests.post(insert_url, headers=post_headers, json=payload)
        if res_post.status_code in [200, 201]:
            return res_post.json()[0]
        else:
            error_msg = f"Failed to create user in Supabase: {res_post.status_code} - {res_post.text}"
            print(f"Supabase user insert error: {error_msg}")
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"Supabase register exception: {str(e)}"
        print(error_msg)
        return {"error": error_msg}

def login_supabase_user(email, password):
    url = f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{email}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200 and len(res.json()) > 0:
            user = res.json()[0]
            if check_password_hash(user['password_hash'], password):
                return user
        return None
    except Exception as e:
        print(f"Supabase login exception: {e}")
        return None

def get_supabase_notifications(user_id):
    url = f"{SUPABASE_URL}/rest/v1/notifications?user_id=eq.{user_id}&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        print(f"Supabase notifications fetch error: {e}")
        return []

def add_supabase_notification(user_id, title, message, notification_type='info'):
    url = f"{SUPABASE_URL}/rest/v1/notifications"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "user_id": str(user_id),
        "title": title,
        "message": message,
        "type": notification_type,
        "is_read": False
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code not in [200, 201]:
            print(f"Supabase notification insert error: {res.status_code} {res.text}")
    except Exception as e:
        print(f"Supabase notification insert exception: {e}")

def create_notification(user_id, title, message, notification_type='info'):
    if DB_BACKEND == 'supabase':
        add_supabase_notification(user_id, title, message, notification_type)
    elif DB_BACKEND == 'sqlite':
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, ?, ?, ?)
            ''', (user_id, title, message, notification_type))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"SQLite notification insert error: {e}")
    else:
        mock_notifications.append({
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "created_at": datetime.now().isoformat()
        })

# Initialize MongoDB if selected
if DB_BACKEND == 'mongodb':
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/smartfridge")
    mongo = PyMongo(app)

# SQLite database path
SQLITE_DB = 'smart_fridge.db'

# Initialize SQLite database schema if file is empty/missing
def init_sqlite_db():
    if not HAS_SQLITE:
        return
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            household VARCHAR(100),
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consumption_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER,
            item_name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            quantity_consumed DECIMAL(10,2) NOT NULL,
            quantity_unit VARCHAR(20) DEFAULT 'pieces',
            consumed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            days_before_expiry INTEGER,
            consumption_reason VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_food_items_user_id ON food_items(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_food_items_expiry ON food_items(expiry_date)')
    conn.commit()
    conn.close()

if DB_BACKEND == 'sqlite':
    init_sqlite_db()
    if HAS_ML_ENGINE:
        ml_engine = MLEngine(SQLITE_DB)

# Mock Data Storage (In-memory fallback)
mock_users = {
    "demo": {
        "id": "demo",
        "username": "demo_user",
        "email": "demo@example.com",
        "password": generate_password_hash("password"),
        "household": "Demo Household",
        "preferences": {}
    }
}

mock_inventory = [
    {
        "id": "1",
        "user_id": "demo",
        "name": "Milk",
        "category": "Dairy",
        "quantity": 1.0,
        "quantity_unit": "liters",
        "storage_location": "Shelf",
        "expiry_date": (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
        "has_expiry": True,
        "days_left": 2,
        "priority_score": 90
    },
    {
        "id": "2",
        "user_id": "demo",
        "name": "Bananas",
        "category": "Fruits",
        "quantity": 6.0,
        "quantity_unit": "pieces",
        "storage_location": "Shelf",
        "expiry_date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
        "has_expiry": True,
        "days_left": 3,
        "priority_score": 80
    },
    {
        "id": "3",
        "user_id": "demo",
        "name": "Bread",
        "category": "Packaged",
        "quantity": 1.0,
        "quantity_unit": "pieces",
        "storage_location": "Shelf",
        "expiry_date": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        "has_expiry": True,
        "days_left": 5,
        "priority_score": 60
    },
    {
        "id": "4",
        "user_id": "demo",
        "name": "Apples",
        "category": "Fruits",
        "quantity": 8.0,
        "quantity_unit": "pieces",
        "storage_location": "Drawer",
        "expiry_date": (datetime.now() + timedelta(days=13)).strftime('%Y-%m-%d'),
        "has_expiry": True,
        "days_left": 13,
        "priority_score": 30
    },
    {
        "id": "5",
        "user_id": "demo",
        "name": "Yogurt",
        "category": "Dairy",
        "quantity": 2.0,
        "quantity_unit": "pieces",
        "storage_location": "Shelf",
        "expiry_date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        "has_expiry": True,
        "days_left": -1,
        "priority_score": 100
    }
]

# Helper function to get SQLite connection
def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    
    if DB_BACKEND == 'mongodb':
        # Check exists
        if mongo.db.users.find_one({"email": data['email']}):
            return jsonify({"error": "Email already exists"}), 400
        
        user = {
            "username": data['username'],
            "email": data['email'],
            "password": hashed_password,
            "household": data.get('household', ''),
            "preferences": data.get('preferences', {}),
            "created_at": datetime.now()
        }
        mongo.db.users.insert_one(user)
        return jsonify({"message": "User registered successfully"})

    elif DB_BACKEND == 'sqlite':
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, household, preferences)
                VALUES (?, ?, ?, ?, ?)
            ''', (data['username'], data['email'], hashed_password, data.get('household', ''), json.dumps(data.get('preferences', {}))))
            conn.commit()
            conn.close()
            return jsonify({"message": "User registered successfully"})
        except sqlite3.IntegrityError:
            return jsonify({"error": "Email or username already exists"}), 400

    elif DB_BACKEND == 'supabase':
        res = register_supabase_user(data['username'], data['email'], hashed_password, data.get('household', ''))
        if "error" in res:
            return jsonify({"error": res["error"]}), 400
        return jsonify({"message": "User registered successfully"})

    else: # mock
        if data['email'] in [u['email'] for u in mock_users.values()]:
            return jsonify({"error": "Email already exists"}), 400
        
        user_id = str(len(mock_users) + 1)
        mock_users[user_id] = {
            "id": user_id,
            "username": data['username'],
            "email": data['email'],
            "password": hashed_password,
            "household": data.get('household', ''),
            "preferences": {}
        }
        return jsonify({"message": "User registered successfully"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    
    if DB_BACKEND == 'mongodb':
        user = mongo.db.users.find_one({"email": data['email']})
        if user and check_password_hash(user['password'], data['password']):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            return jsonify({
                "token": "mongo-token",
                "user": {"id": str(user['_id']), "username": user['username'], "email": user['email']}
            })
            
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (data['email'],)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], data['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({
                "token": "sqlite-token",
                "user": {"id": user['id'], "username": user['username'], "email": user['email']}
            })

    elif DB_BACKEND == 'supabase':
        user = login_supabase_user(data['email'], data['password'])
        if user:
            session['user_id'] = str(user['id'])
            session['username'] = user['username']
            return jsonify({
                "token": "supabase-token",
                "user": {"id": str(user['id']), "username": user['username'], "email": user['email']}
            })

    else: # mock
        for u in mock_users.values():
            if u['email'] == data['email'] and check_password_hash(u['password'], data['password']):
                session['user_id'] = u['id']
                session['username'] = u['username']
                return jsonify({
                    "token": "mock-token",
                    "user": {"id": u['id'], "username": u['username'], "email": u['email']}
                })
                
    return jsonify({"error": "Invalid credentials"}), 401

# ---------------------------------------------------------
# Page & Static Content Delivery
# ---------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(base_dir, 'static'), filename)

# ---------------------------------------------------------
# Inventory Dashboard & CRUD
# ---------------------------------------------------------
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    items = []
    
    if DB_BACKEND == 'mongodb':
        mongo_items = list(mongo.db.food.find({"user_id": user_id}))
        for mi in mongo_items:
            mi['id'] = str(mi['_id'])
            del mi['_id']
            items.append(mi)
            
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        db_items = conn.execute('SELECT * FROM food_items WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        for di in db_items:
            dict_item = dict(di)
            dict_item['expiry'] = dict_item['expiry_date']
            items.append(dict_item)
            
    elif DB_BACKEND == 'supabase':
        items = get_supabase_items(user_id)
        
    else: # mock
        items = [dict(i) for i in mock_inventory if i['user_id'] == user_id]

    # Calculate dashboard metrics
    total_items = len(items)
    expiring_soon = len([item for item in items if item.get('days_left', 0) <= 3 and item.get('days_left', 0) >= 0])
    low_stock = len([item for item in items if float(item.get('quantity', 0)) <= 2])
    expired = len([item for item in items if item.get('days_left', 0) < 0])
    
    # Priority-based ranking
    for item in items:
        item['priority_score'] = calculate_priority_score(item)
    
    items.sort(key=lambda x: x['priority_score'], reverse=True)
    
    return jsonify({
        "total_items": total_items,
        "expiring_soon": expiring_soon,
        "low_stock": low_stock,
        "expired": expired,
        "items": items[:10],
        "categories": get_category_distribution(items)
    })

@app.route('/add', methods=['POST'])
def add_food():
    data = request.json
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    expiry = datetime.strptime(data['expiry'], "%Y-%m-%d")
    days_left = (expiry - datetime.today()).days
    priority_score = calculate_priority_score({"days_left": days_left, "quantity": data['quantity']})
    
    item_id = None
    if DB_BACKEND == 'mongodb':
        food_item = {
            "user_id": user_id,
            "name": data['name'],
            "category": data['category'],
            "quantity": float(data['quantity']),
            "quantity_unit": data.get('quantity_unit', 'pieces'),
            "storage_location": data.get('storage_location', 'Shelf'),
            "expiry": data['expiry'],
            "days_left": days_left,
            "priority_score": priority_score,
            "freshness_status": "Unknown",
            "usage_frequency": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        res = mongo.db.food.insert_one(food_item)
        item_id = str(res.inserted_id)

    elif DB_BACKEND == 'sqlite':
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO food_items (user_id, name, category, quantity, quantity_unit, storage_location, expiry_date, days_left, priority_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, data['name'], data['category'], float(data['quantity']), data.get('quantity_unit', 'pieces'), data.get('storage_location', 'Shelf'), data['expiry'], days_left, priority_score))
            item_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif DB_BACKEND == 'supabase':
        ret = add_supabase_item(user_id, {
            "name": data['name'],
            "category": data['category'],
            "quantity": float(data['quantity']),
            "quantity_unit": data.get('quantity_unit', 'pieces'),
            "storage_location": data.get('storage_location', 'Shelf'),
            "expiry": data['expiry'],
            "days_left": days_left,
            "priority_score": priority_score
        })
        if ret:
            item_id = ret['id']
        else:
            return jsonify({"error": "Failed to add item to Supabase"}), 500

    else: # mock
        item_id = str(len(mock_inventory) + 1)
        mock_item = {
            "id": item_id,
            "user_id": user_id,
            "name": data['name'],
            "category": data['category'],
            "quantity": float(data['quantity']),
            "quantity_unit": data.get('quantity_unit', 'pieces'),
            "storage_location": data.get('storage_location', 'Shelf'),
            "expiry_date": data['expiry'],
            "days_left": days_left,
            "priority_score": priority_score
        }
        mock_inventory.append(mock_item)

    create_notification(user_id, "Item Added", f"'{data['name']}' has been added to storage location: {data.get('storage_location', 'Shelf')}.", "info")
    return jsonify({"message": "Item Added", "item_id": item_id, "priority_score": priority_score})

@app.route('/items')
def get_items():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    items = []
    
    if DB_BACKEND == 'mongodb':
        mongo_items = list(mongo.db.food.find({"user_id": user_id}))
        for mi in mongo_items:
            mi['id'] = str(mi['_id'])
            del mi['_id']
            items.append(mi)
            
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        db_items = conn.execute('SELECT * FROM food_items WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        for di in db_items:
            dict_item = dict(di)
            dict_item['id'] = dict_item['id']
            dict_item['expiry'] = dict_item['expiry_date']
            items.append(dict_item)
            
    elif DB_BACKEND == 'supabase':
        items = get_supabase_items(user_id)
        
    else: # mock
        items = [dict(i) for i in mock_inventory if i['user_id'] == user_id]

    for item in items:
        # Calculate/refresh days left
        if 'expiry' in item and item['expiry']:
            expiry = datetime.strptime(item['expiry'], "%Y-%m-%d")
            item['days_left'] = (expiry - datetime.today()).days
        elif 'expiry_date' in item and item['expiry_date']:
            expiry = datetime.strptime(item['expiry_date'], "%Y-%m-%d")
            item['days_left'] = (expiry - datetime.today()).days
            
        item['priority_score'] = calculate_priority_score(item)
        item['expiry_risk'] = get_expiry_risk(item.get('days_left', 0))
        item['freshness_color'] = get_freshness_color(item.get('days_left', 0))
        
    return jsonify(items)

@app.route('/update/<item_id>', methods=['PUT'])
def update_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    
    # Calculate values
    days_left = 0
    if 'expiry' in data:
        expiry = datetime.strptime(data['expiry'], "%Y-%m-%d")
        days_left = (expiry - datetime.today()).days
        
    priority_score = calculate_priority_score({"days_left": days_left, "quantity": data['quantity']})
    
    success = False
    if DB_BACKEND == 'mongodb':
        update_data = {
            "name": data['name'],
            "category": data['category'],
            "quantity": float(data['quantity']),
            "quantity_unit": data.get('quantity_unit', 'pieces'),
            "storage_location": data.get('storage_location', 'Shelf'),
            "expiry": data['expiry'],
            "days_left": days_left,
            "priority_score": priority_score,
            "updated_at": datetime.now()
        }
        mongo.db.food.update_one({"_id": ObjectId(item_id), "user_id": user_id}, {"$set": update_data})
        success = True
        
    elif DB_BACKEND == 'sqlite':
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE food_items
                SET name = ?, category = ?, quantity = ?, quantity_unit = ?, storage_location = ?, expiry_date = ?, days_left = ?, priority_score = ?
                WHERE user_id = ? AND id = ?
            ''', (data['name'], data['category'], float(data['quantity']), data.get('quantity_unit', 'pieces'), data.get('storage_location', 'Shelf'), data['expiry'], days_left, priority_score, user_id, int(item_id)))
            conn.commit()
            conn.close()
            success = True
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif DB_BACKEND == 'supabase':
        success = update_supabase_item(user_id, item_id, {
            "name": data['name'],
            "category": data['category'],
            "quantity": float(data['quantity']),
            "quantity_unit": data.get('quantity_unit', 'pieces'),
            "storage_location": data.get('storage_location', 'Shelf'),
            "expiry": data['expiry'],
            "days_left": days_left,
            "priority_score": priority_score
        })
            
    else: # mock
        for item in mock_inventory:
            if item['id'] == item_id and item['user_id'] == user_id:
                item['name'] = data['name']
                item['category'] = data['category']
                item['quantity'] = float(data['quantity'])
                item['quantity_unit'] = data.get('quantity_unit', 'pieces')
                item['storage_location'] = data.get('storage_location', 'Shelf')
                item['expiry_date'] = data['expiry']
                item['days_left'] = days_left
                item['priority_score'] = priority_score
                success = True
                break
                
    if success:
        create_notification(user_id, "Item Updated", f"'{data['name']}' has been updated successfully.", "info")
        return jsonify({"message": "Item updated"})
    else:
        return jsonify({"error": "Failed to update item"}), 500

@app.route('/delete/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    success = False
    if DB_BACKEND == 'mongodb':
        mongo.db.food.delete_one({"_id": ObjectId(item_id), "user_id": user_id})
        success = True
        
    elif DB_BACKEND == 'sqlite':
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM food_items WHERE user_id = ? AND id = ?', (user_id, int(item_id)))
            conn.commit()
            conn.close()
            success = True
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif DB_BACKEND == 'supabase':
        success = delete_supabase_item(user_id, item_id)
            
    else: # mock
        global mock_inventory
        mock_inventory = [i for i in mock_inventory if not (i['id'] == item_id and i['user_id'] == user_id)]
        success = True
        
    if success:
        create_notification(user_id, "Item Deleted", "An item was removed from the inventory.", "info")
        return jsonify({"message": "Deleted"})
    else:
        return jsonify({"error": "Failed to delete item"}), 500

# ---------------------------------------------------------
# Expiry & Alerts Endpoint
# ---------------------------------------------------------
@app.route('/api/alerts')
def get_alerts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    items = []
    
    if DB_BACKEND == 'mongodb':
        mongo_items = list(mongo.db.food.find({"user_id": user_id}))
        for mi in mongo_items:
            mi['id'] = str(mi['_id'])
            del mi['_id']
            items.append(mi)
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        db_items = conn.execute('SELECT * FROM food_items WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        for di in db_items:
            dict_item = dict(di)
            dict_item['expiry'] = dict_item['expiry_date']
            items.append(dict_item)
    elif DB_BACKEND == 'supabase':
        items = get_supabase_items(user_id)
    else:
        items = [dict(i) for i in mock_inventory if i['user_id'] == user_id]
        
    expired = []
    expiring_soon = []
    low_stock = []
    
    for item in items:
        days_left = item.get('days_left', 0)
        quantity = float(item.get('quantity', 1))
        unit = item.get('quantity_unit', 'pieces')
        
        # Check expired
        if days_left < 0:
            expired.append(item)
        # Check expiring soon (0 to 3 days)
        elif 0 <= days_left <= 3:
            expiring_soon.append(item)
            
        # Check low stock
        is_low = False
        if unit in ['pieces', 'dozen'] and quantity <= 2:
            is_low = True
        elif unit in ['kg', 'lb', 'liters'] and quantity <= 0.5:
            is_low = True
        elif unit in ['g', 'ml', 'oz'] and quantity <= 200:
            is_low = True
            
        if is_low:
            low_stock.append(item)
            
    return jsonify({
        "expired": expired,
        "expiring_soon": expiring_soon,
        "low_stock": low_stock
    })

# In-memory notifications store for mock backend
mock_notifications = []

@app.route('/api/notifications', methods=['GET', 'POST'])
def get_or_post_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'POST':
        data = request.json
        title = data.get('title', 'Smart Alert')
        message = data.get('message', '')
        type_ = data.get('type', 'info')
        
        if DB_BACKEND == 'supabase':
            add_supabase_notification(user_id, title, message, type_)
        elif DB_BACKEND == 'sqlite':
            try:
                conn = get_sqlite_conn()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, title, message, type_))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"SQLite notification insert error: {e}")
        else:
            mock_notifications.append({
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": type_,
                "created_at": datetime.now().isoformat()
            })
        return jsonify({"message": "Notification added"})
        
    # GET method
    notifications_list = []
    if DB_BACKEND == 'supabase':
        notifications_list = get_supabase_notifications(user_id)
    elif DB_BACKEND == 'sqlite':
        try:
            conn = get_sqlite_conn()
            db_notifs = conn.execute('SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 50', (user_id,)).fetchall()
            conn.close()
            notifications_list = [dict(n) for n in db_notifs]
        except Exception as e:
            print(f"SQLite notification fetch error: {e}")
    else:
        notifications_list = [n for n in mock_notifications if n['user_id'] == user_id]
        
    return jsonify(notifications_list)

# ---------------------------------------------------------
# ML and Analytics Endpoints
# ---------------------------------------------------------
@app.route('/predict-consumption', methods=['POST'])
def predict_consumption():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch user's active items
    items = []
    if DB_BACKEND == 'mongodb':
        items = list(mongo.db.food.find({"user_id": user_id}))
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        db_items = conn.execute('SELECT * FROM food_items WHERE user_id = ? AND days_left >= 0', (user_id,)).fetchall()
        conn.close()
        items = [dict(di) for di in db_items]
    elif DB_BACKEND == 'supabase':
        items = [i for i in get_supabase_items(user_id) if i.get('days_left', 0) >= 0]
    else:
        items = [dict(i) for i in mock_inventory if i['user_id'] == user_id]

    predictions = []
    for item in items:
        # Mock ML probability score generation
        days = float(item.get('days_left', 5))
        qty = float(item.get('quantity', 1))
        
        # Calculate mock prediction values that are deterministic and sensible
        knn = max(0.1, min(0.9, 0.9 - (days * 0.05)))
        nb = max(0.1, min(0.9, 0.85 - (days * 0.04) + (qty * 0.02)))
        dt = max(0.1, min(0.9, 0.78 - (days * 0.06)))
        
        predictions.append({
            "item_name": item['name'],
            "knn_prediction": float(knn),
            "nb_prediction": float(nb),
            "dt_prediction": float(dt),
            "ensemble_prediction": float((knn + nb + dt) / 3)
        })

    return jsonify({"predictions": predictions})

@app.route('/analytics')
def analytics():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    items = []
    if DB_BACKEND == 'mongodb':
        items = list(mongo.db.food.find({"user_id": user_id}))
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        db_items = conn.execute('SELECT * FROM food_items WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        items = [dict(di) for di in db_items]
    elif DB_BACKEND == 'supabase':
        items = get_supabase_items(user_id)
    else:
        items = [dict(i) for i in mock_inventory if i['user_id'] == user_id]

    # Basic statistics
    expired_count = len([item for item in items if item.get('days_left', 0) < 0])
    waste_rate = expired_count / len(items) if items else 0.0
    
    # Categorization
    categories = get_category_distribution(items)

    # Simulated Cluster Analysis
    cluster_analysis = [
        {
            "cluster_id": 0,
            "count": len([i for i in items if i.get('days_left', 0) <= 3]),
            "avg_days_left": 1.5,
            "avg_quantity": 2.1,
            "items": [i for i in items if i.get('days_left', 0) <= 3][:3]
        },
        {
            "cluster_id": 1,
            "count": len([i for i in items if 3 < i.get('days_left', 0) <= 10]),
            "avg_days_left": 6.8,
            "avg_quantity": 4.5,
            "items": [i for i in items if 3 < i.get('days_left', 0) <= 10][:3]
        },
        {
            "cluster_id": 2,
            "count": len([i for i in items if i.get('days_left', 0) > 10]),
            "avg_days_left": 15.2,
            "avg_quantity": 8.0,
            "items": [i for i in items if i.get('days_left', 0) > 10][:3]
        }
    ]

    monthly_trends = [
        {"month": "Jan", "consumed": 45, "wasted": 5},
        {"month": "Feb", "consumed": 52, "wasted": 3},
        {"month": "Mar", "consumed": 48, "wasted": 7},
        {"month": "Apr", "consumed": 61, "wasted": 4},
        {"month": "May", "consumed": 55, "wasted": 6},
        {"month": "Jun", "consumed": 58, "wasted": 2}
    ]

    return jsonify({
        "clusters": cluster_analysis,
        "waste_rate": waste_rate,
        "monthly_trends": monthly_trends,
        "category_distribution": categories,
        "sustainability_score": max(0, int(100 - (waste_rate * 100)))
    })

@app.route('/risk-heatmap')
def risk_heatmap():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    items = []
    if DB_BACKEND == 'mongodb':
        items = list(mongo.db.food.find({"user_id": user_id}))
    elif DB_BACKEND == 'sqlite':
        conn = get_sqlite_conn()
        db_items = conn.execute('SELECT * FROM food_items WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        items = [dict(di) for di in db_items]
    else:
        items = [dict(i) for i in mock_inventory if i['user_id'] == user_id]

    categories = ['Fruits', 'Vegetables', 'Dairy', 'Packaged', 'Meat', 'Other']
    risk_grid = []
    
    for category in categories:
        cat_items = [i for i in items if i.get('category') == category]
        if cat_items:
            avg_risk = sum([get_risk_score(i.get('days_left', 0)) for i in cat_items]) / len(cat_items)
            risk_grid.append({
                "category": category,
                "risk_level": get_risk_level(avg_risk),
                "risk_score": avg_risk,
                "item_count": len(cat_items),
                "color": get_risk_color(avg_risk)
            })
            
    return jsonify({"risk_grid": risk_grid})

# ---------------------------------------------------------
# Freshness Detection (Computer Vision)
# ---------------------------------------------------------
@app.route('/detect-freshness', methods=['POST'])
def detect_freshness():
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({"error": "No image provided"}), 400
            
        if not HAS_CV:
            # Safe mock fallback if OpenCV/PIL are not installed
            return jsonify({
                "freshness": "Fresh",
                "confidence": 0.85,
                "color_analysis": {
                    "mean_hue": 45.0,
                    "mean_saturation": 120.0,
                    "mean_value": 180.0
                }
            })
            
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(image)
        
        # CV color statistics
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        mean_hue = np.mean(hsv[:, :, 0])
        mean_saturation = np.mean(hsv[:, :, 1])
        mean_value = np.mean(hsv[:, :, 2])
        
        if mean_saturation > 100 and mean_value > 150:
            freshness = "Fresh"
            confidence = 0.8
        elif mean_saturation > 50:
            freshness = "Ripe"
            confidence = 0.6
        else:
            freshness = "Overripe"
            confidence = 0.7
            
        return jsonify({
            "freshness": freshness,
            "confidence": confidence,
            "color_analysis": {
                "mean_hue": float(mean_hue),
                "mean_saturation": float(mean_saturation),
                "mean_value": float(mean_value)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def calculate_priority_score(item):
    days_left = item.get('days_left', 0)
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

def get_category_distribution(items):
    categories = {}
    for item in items:
        cat = item.get('category', 'Other')
        categories[cat] = categories.get(cat, 0) + 1
    return categories

if __name__ == '__main__':
    print("Starting Smart Fridge AI Consolidated Server...")
    print("Open your browser to: http://localhost:5000")
    app.run(debug=False, port=5000)
