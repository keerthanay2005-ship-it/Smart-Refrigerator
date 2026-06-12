from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from twilio.rest import Client
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'demo-secret-key-for-testing')
CORS(app)

# Twilio configuration
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
twilio_client = None

if twilio_account_sid and twilio_auth_token:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)

# Mock data for demo purposes
mock_users = {}
mock_inventory = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_id = f"user_{len(mock_users) + 1}"
    mock_users[user_id] = {
        'id': user_id,
        'username': data['username'],
        'email': data['email'],
        'phone': data.get('phone', ''),
        'password': data['password'],  # In production, hash this!
        'household': data.get('household', ''),
        'created_at': datetime.now()
    }
    return jsonify({"message": "User registered successfully", "user_id": user_id})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    for user_id, user in mock_users.items():
        if user['email'] == data['email'] and user['password'] == data['password']:
            session['user_id'] = user_id
            return jsonify({
                "token": "demo-token",
                "user": {
                    "id": user_id,
                    "username": user['username'],
                    "email": user['email']
                }
            })
    
    # For demo, create a user if not found
    user_id = f"demo_{data['email']}"
    mock_users[user_id] = {
        'id': user_id,
        'username': data['email'].split('@')[0],
        'email': data['email'],
        'password': data['password'],
        'created_at': datetime.now()
    }
    session['user_id'] = user_id
    return jsonify({
        "token": "demo-token",
        "user": {
            "id": user_id,
            "username": mock_users[user_id]['username'],
            "email": data['email']
        }
    })

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get user's items
    user_items = [item for item in mock_inventory if item.get('user_id') == user_id]
    
    # Calculate metrics
    total_items = len(user_items)
    expiring_soon = len([item for item in user_items if item.get('days_left', 0) <= 3])
    low_stock = len([item for item in user_items if item.get('quantity', 0) <= 2])
    expired = len([item for item in user_items if item.get('days_left', 0) < 0])
    
    # Sort by priority
    for item in user_items:
        item['priority_score'] = calculate_priority_score(item)
    
    user_items.sort(key=lambda x: x['priority_score'], reverse=True)
    
    return jsonify({
        "total_items": total_items,
        "expiring_soon": expiring_soon,
        "low_stock": low_stock,
        "expired": expired,
        "items": user_items[:10],
        "categories": get_category_distribution(user_items)
    })

@app.route('/add', methods=['POST'])
def add_food():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    expiry = datetime.strptime(data['expiry'], "%Y-%m-%d")
    days_left = (expiry - datetime.today()).days
    
    food_item = {
        "_id": f"item_{len(mock_inventory) + 1}",
        "user_id": user_id,
        "name": data['name'],
        "category": data['category'],
        "quantity": float(data['quantity']),
        "quantity_unit": data.get('quantity_unit', 'pieces'),
        "storage_location": data.get('storage_location', 'Shelf'),
        "expiry": data['expiry'],
        "days_left": days_left,
        "has_expiry": data.get('has_expiry', True),
        "priority_score": 0,
        "freshness_status": "Unknown",
        "usage_frequency": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    food_item['priority_score'] = calculate_priority_score(food_item)
    food_item['expiry_risk'] = get_expiry_risk(days_left)
    food_item['freshness_color'] = get_freshness_color(days_left)
    
    mock_inventory.append(food_item)
    return jsonify({"message": "Item Added", "priority_score": food_item['priority_score']})

@app.route('/items')
def get_items():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_items = [item for item in mock_inventory if item.get('user_id') == user_id]
    
    # Update priority scores and expiry indicators
    for item in user_items:
        item['priority_score'] = calculate_priority_score(item)
        item['expiry_risk'] = get_expiry_risk(item.get('days_left', 0))
        item['freshness_color'] = get_freshness_color(item.get('days_left', 0))
    
    return jsonify(user_items)

@app.route('/update/<item_id>', methods=['PUT'])
def update_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    for item in mock_inventory:
        if item.get('_id') == item_id and item.get('user_id') == user_id:
            item.update(data)
            item['updated_at'] = datetime.now()
            if 'expiry' in data:
                expiry = datetime.strptime(data['expiry'], "%Y-%m-%d")
                item['days_left'] = (expiry - datetime.today()).days
                item['priority_score'] = calculate_priority_score(item)
                item['expiry_risk'] = get_expiry_risk(item['days_left'])
                item['freshness_color'] = get_freshness_color(item['days_left'])
            break
    
    return jsonify({"message": "Item updated"})

@app.route('/delete/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    mock_inventory[:] = [item for item in mock_inventory 
                        if not (item.get('_id') == item_id and item.get('user_id') == user_id)]
    return jsonify({"message": "Deleted"})

@app.route('/detect-freshness', methods=['POST'])
def detect_freshness():
    # Mock freshness detection
    return jsonify({
        "freshness": "Fresh",
        "confidence": 0.85,
        "color_analysis": {
            "mean_hue": 45,
            "mean_saturation": 120,
            "mean_value": 180
        }
    })

@app.route('/predict-consumption', methods=['POST'])
def predict_consumption():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_items = [item for item in mock_inventory if item.get('user_id') == user_id]
    predictions = []
    
    for item in user_items:
        predictions.append({
            "item_name": item['name'],
            "knn_prediction": 0.85,
            "nb_prediction": 0.78,
            "dt_prediction": 0.82,
            "ensemble_prediction": 0.82
        })
    
    return jsonify({"predictions": predictions})

@app.route('/analytics')
def analytics():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_items = [item for item in mock_inventory if item.get('user_id') == user_id]
    
    return jsonify({
        "clusters": [
            {"cluster_id": 0, "count": 5, "avg_days_left": 2, "avg_quantity": 3, "items": ["Milk", "Yogurt"]},
            {"cluster_id": 1, "count": 8, "avg_days_left": 10, "avg_quantity": 5, "items": ["Apples", "Bananas"]},
            {"cluster_id": 2, "count": 2, "avg_days_left": 30, "avg_quantity": 10, "items": ["Frozen items"]}
        ],
        "waste_rate": 15,
        "monthly_trends": [
            {"month": "Jan", "consumed": 45, "wasted": 5},
            {"month": "Feb", "consumed": 52, "wasted": 3},
            {"month": "Mar", "consumed": 48, "wasted": 7},
            {"month": "Apr", "consumed": 61, "wasted": 4},
            {"month": "May", "consumed": 55, "wasted": 6},
            {"month": "Jun", "consumed": 58, "wasted": 2}
        ],
        "category_distribution": get_category_distribution(user_items),
        "sustainability_score": 85
    })

@app.route('/risk-heatmap')
def risk_heatmap():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "risk_grid": [
            {"category": "Fruits", "risk_level": "High", "risk_score": 75, "item_count": 5, "color": "#FFA500"},
            {"category": "Vegetables", "risk_level": "Medium", "risk_score": 45, "item_count": 4, "color": "#FFD700"},
            {"category": "Dairy", "risk_level": "High", "risk_score": 85, "item_count": 3, "color": "#FF6B6B"},
            {"category": "Packaged", "risk_level": "Low", "risk_score": 25, "item_count": 2, "color": "#90EE90"},
            {"category": "Meat", "risk_level": "Critical", "risk_score": 95, "item_count": 1, "color": "#FF0000"},
            {"category": "Other", "risk_level": "Low", "risk_score": 15, "item_count": 3, "color": "#90EE90"}
        ]
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

def get_category_distribution(items):
    categories = {}
    for item in items:
        category = item.get('category', 'Other')
        categories[category] = categories.get(category, 0) + 1
    return categories

def send_sms_notification(phone_number, message):
    """Send SMS notification using Twilio"""
    try:
        if not twilio_client:
            print("Twilio client not configured")
            return False
        
        # Clean phone number format
        phone_number = re.sub(r'[^\d+]', '', phone_number)
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number  # Default to India country code
        
        message = twilio_client.messages.create(
            body=message,
            from_=twilio_phone_number,
            to=phone_number
        )
        print(f"SMS sent successfully: {message.sid}")
        return True
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")
        return False

@app.route('/api/alerts')
def get_alerts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_items = [item for item in mock_inventory if item.get('user_id') == user_id]
    
    expired = []
    expiring_soon = []
    low_stock = []
    
    for item in user_items:
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

def send_expiry_alerts():
    """Send SMS alerts for items expiring soon"""
    for user_id, user in mock_users.items():
        if not user.get('phone'):
            continue
            
        user_items = [item for item in mock_inventory if item.get('user_id') == user_id]
        expiring_soon = []
        
        for item in user_items:
            expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            days_left = (expiry_date - datetime.now().date()).days
            
            if days_left <= 3 and days_left >= 0:
                expiring_soon.append(f"{item['name']} ({days_left} days)")
        
        if expiring_soon:
            message = f"Smart Fridge Alert: Items expiring soon - {', '.join(expiring_soon)}"
            send_sms_notification(user['phone'], message)

if __name__ == '__main__':
    print("Starting Smart Fridge AI Demo Server...")
    print("Open your browser to: http://localhost:5000")
    app.run(debug=False, port=5000)
