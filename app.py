
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
import pandas as pd
import os
from dotenv import load_dotenv
import cv2
from PIL import Image
import io
import base64

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
CORS(app)
app.config["MONGO_URI"] = "mongodb://localhost:27017/smartfridge"
mongo = PyMongo(app)

# ML Models
knn_model = KNeighborsClassifier(n_neighbors=5)
nb_model = GaussianNB()
dt_model = DecisionTreeClassifier(random_state=42)
scaler = StandardScaler()

# User Management
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    
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

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = mongo.db.users.find_one({"email": data['email']})
    
    if user and check_password_hash(user['password'], data['password']):
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.secret_key, algorithm='HS256')
        
        session['user_id'] = str(user['_id'])
        return jsonify({
            "token": token,
            "user": {
                "id": str(user['_id']),
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
    
    # Get all items for user
    items = list(mongo.db.food.find({"user_id": user_id}, {'_id': 0}))
    
    # Calculate dashboard metrics
    total_items = len(items)
    expiring_soon = len([item for item in items if item.get('days_left', 0) <= 3])
    low_stock = len([item for item in items if item.get('quantity', 0) <= 2])
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
        "items": items[:10],  # Top 10 priority items
        "categories": get_category_distribution(items)
    })

# Food Inventory Management
@app.route('/add', methods=['POST'])
def add_food():
    data = request.json
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    expiry = datetime.strptime(data['expiry'], "%Y-%m-%d")
    days_left = (expiry - datetime.today()).days
    
    food_item = {
        "user_id": user_id,
        "name": data['name'],
        "category": data['category'],
        "quantity": int(data['quantity']),
        "storage_location": data.get('storage_location', 'Shelf'),
        "expiry": data['expiry'],
        "days_left": days_left,
        "priority_score": 0,
        "freshness_status": "Unknown",
        "usage_frequency": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    food_item['priority_score'] = calculate_priority_score(food_item)
    
    mongo.db.food.insert_one(food_item)
    return jsonify({"message": "Item Added", "priority_score": food_item['priority_score']})

@app.route('/items')
def get_items():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    items = list(mongo.db.food.find({"user_id": user_id}, {'_id': 0}))
    
    # Update priority scores and expiry indicators
    for item in items:
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
    update_data = data.copy()
    update_data['updated_at'] = datetime.now()
    
    if 'expiry' in update_data:
        expiry = datetime.strptime(update_data['expiry'], "%Y-%m-%d")
        update_data['days_left'] = (expiry - datetime.today()).days
    
    mongo.db.food.update_one(
        {"_id": item_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    return jsonify({"message": "Item updated"})

@app.route('/delete/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    mongo.db.food.delete_one({"_id": item_id, "user_id": user_id})
    return jsonify({"message": "Deleted"})

# Freshness Detection (Computer Vision)
@app.route('/detect-freshness', methods=['POST'])
def detect_freshness():
    try:
        # Get image data
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({"error": "No image provided"}), 400
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(image)
        
        # Basic freshness detection using color analysis
        freshness_result = analyze_freshness(img_array)
        
        return jsonify(freshness_result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Machine Learning Features
@app.route('/predict-consumption', methods=['POST'])
def predict_consumption():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get user's consumption history
    history = list(mongo.db.consumption_history.find({"user_id": user_id}, {'_id': 0}))
    
    if len(history) < 5:
        return jsonify({"error": "Insufficient data for prediction"}), 400
    
    # Prepare data for ML models
    df = pd.DataFrame(history)
    
    # Feature engineering
    features = ['days_left', 'quantity', 'usage_frequency']
    X = df[features].values
    y = df['consumed'].values
    
    # Scale features
    X_scaled = scaler.fit_transform(X)
    
    # Train models
    knn_model.fit(X_scaled, y)
    nb_model.fit(X_scaled, y)
    dt_model.fit(X_scaled, y)
    
    # Get current items for prediction
    current_items = list(mongo.db.food.find({"user_id": user_id}, {'_id': 0}))
    predictions = []
    
    for item in current_items:
        item_features = [[
            item.get('days_left', 0),
            item.get('quantity', 1),
            item.get('usage_frequency', 0)
        ]]
        
        item_features_scaled = scaler.transform(item_features)
        
        knn_pred = knn_model.predict(item_features_scaled)[0]
        nb_pred = nb_model.predict(item_features_scaled)[0]
        dt_pred = dt_model.predict(item_features_scaled)[0]
        
        # Ensemble prediction
        ensemble_pred = (knn_pred + nb_pred + dt_pred) / 3
        
        predictions.append({
            "item_name": item['name'],
            "knn_prediction": float(knn_pred),
            "nb_prediction": float(nb_pred),
            "dt_prediction": float(dt_pred),
            "ensemble_prediction": float(ensemble_pred)
        })
    
    return jsonify({"predictions": predictions})

# Clustering and Analytics
@app.route('/analytics')
def analytics():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    items = list(mongo.db.food.find({"user_id": user_id}, {'_id': 0}))
    
    if len(items) < 3:
        return jsonify({"error": "Insufficient data for analytics"}), 400
    
    # Prepare data for clustering
    df = pd.DataFrame(items)
    features = ['days_left', 'quantity', 'usage_frequency']
    
    # Handle missing values
    for feature in features:
        if feature not in df.columns:
            df[feature] = 0
    
    X = df[features].fillna(0).values
    
    # K-Means clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    clusters = kmeans.fit_predict(X)
    
    # Analyze clusters
    cluster_analysis = []
    for i in range(3):
        cluster_items = [items[j] for j in range(len(items)) if clusters[j] == i]
        cluster_analysis.append({
            "cluster_id": i,
            "count": len(cluster_items),
            "avg_days_left": np.mean([item.get('days_left', 0) for item in cluster_items]),
            "avg_quantity": np.mean([item.get('quantity', 0) for item in cluster_items]),
            "items": cluster_items[:5]  # Sample items
        })
    
    # Waste analysis
    expired_items = [item for item in items if item.get('days_left', 0) < 0]
    waste_rate = len(expired_items) / len(items) if items else 0
    
    # Monthly trends (mock data for demo)
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
        "category_distribution": get_category_distribution(items),
        "sustainability_score": max(0, 100 - (waste_rate * 100))
    })

# Expiry Risk Heatmap
@app.route('/risk-heatmap')
def risk_heatmap():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    items = list(mongo.db.food.find({"user_id": user_id}, {'_id': 0}))
    
    # Create grid-based risk display
    risk_grid = []
    categories = ['Fruits', 'Vegetables', 'Dairy', 'Packaged', 'Meat', 'Other']
    
    for category in categories:
        category_items = [item for item in items if item.get('category') == category]
        
        if category_items:
            avg_risk = np.mean([get_risk_score(item.get('days_left', 0)) for item in category_items])
            risk_level = get_risk_level(avg_risk)
            
            risk_grid.append({
                "category": category,
                "risk_level": risk_level,
                "risk_score": avg_risk,
                "item_count": len(category_items),
                "color": get_risk_color(avg_risk)
            })
    
    return jsonify({"risk_grid": risk_grid})

# Helper Functions
def calculate_priority_score(item):
    days_left = item.get('days_left', 0)
    quantity = item.get('quantity', 1)
    usage_freq = item.get('usage_frequency', 1)
    
    # Priority formula: higher score = consume first
    if days_left < 0:
        return 100  # Expired items get highest priority
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
        return "#FF0000"  # Red
    elif days_left <= 3:
        return "#FF6B6B"  # Light Red
    elif days_left <= 7:
        return "#FFA500"  # Orange
    elif days_left <= 14:
        return "#FFD700"  # Yellow
    else:
        return "#90EE90"  # Light Green

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
        return "#FF0000"  # Red
    elif score >= 50:
        return "#FFA500"  # Orange
    else:
        return "#90EE90"  # Green

def get_category_distribution(items):
    categories = {}
    for item in items:
        category = item.get('category', 'Other')
        categories[category] = categories.get(category, 0) + 1
    
    return categories

def analyze_freshness(img_array):
    # Simple color-based freshness analysis
    # Convert to HSV for better color analysis
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # Calculate color statistics
    mean_hue = np.mean(hsv[:, :, 0])
    mean_saturation = np.mean(hsv[:, :, 1])
    mean_value = np.mean(hsv[:, :, 2])
    
    # Simple freshness classification based on color
    if mean_saturation > 100 and mean_value > 150:
        freshness = "Fresh"
        confidence = 0.8
    elif mean_saturation > 50:
        freshness = "Ripe"
        confidence = 0.6
    else:
        freshness = "Overripe"
        confidence = 0.7
    
    return {
        "freshness": freshness,
        "confidence": confidence,
        "color_analysis": {
            "mean_hue": float(mean_hue),
            "mean_saturation": float(mean_saturation),
            "mean_value": float(mean_value)
        }
    }

@app.route('/api/alerts')
def get_alerts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    items = list(mongo.db.food.find({"user_id": user_id}))
    
    expired = []
    expiring_soon = []
    low_stock = []
    
    for item in items:
        # Convert _id to string for JSON serialization
        if '_id' in item:
            item['_id'] = str(item['_id'])
            
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

if __name__ == '__main__':
    app.run(debug=True)
