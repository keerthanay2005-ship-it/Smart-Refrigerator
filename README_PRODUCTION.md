# Smart Fridge AI - Production Setup Guide

## 🚀 Real Database + ML Implementation

### **📊 What's Different from Demo**

| Feature | Demo Version | Production Version |
|---------|---------------|-------------------|
| **Database** | Python lists (memory) | SQLite database (persistent) |
| **ML Models** | Mock predictions | Real trained models |
| **Data Storage** | Session only | Permanent storage |
| **User Data** | Single user | Multi-user support |
| **Learning** | No learning | Improves with usage |
| **Scalability** | Limited | Highly scalable |

---

## 🛠️ **Setup Instructions**

### **Step 1: Install Dependencies**
```bash
pip install -r requirements_production.txt
```

### **Step 2: Run Setup Script**
```bash
python setup_production.py
```

### **Step 3: Start Production Server**
```bash
python app_production.py
```

### **Step 4: Access the Application**
Open: **http://localhost:5000**

---

## 🗄️ **Database Schema**

### **Users Table**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    household VARCHAR(100),
    preferences TEXT,
    created_at TIMESTAMP
);
```

### **Food Items Table**
```sql
CREATE TABLE food_items (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    name VARCHAR(100),
    category VARCHAR(50),
    quantity DECIMAL(10,2),
    quantity_unit VARCHAR(20),
    storage_location VARCHAR(20),
    expiry_date DATE,
    days_left INTEGER,
    priority_score INTEGER,
    created_at TIMESTAMP
);
```

### **Consumption History Table**
```sql
CREATE TABLE consumption_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    item_name VARCHAR(100),
    category VARCHAR(50),
    quantity_consumed DECIMAL(10,2),
    consumed_date TIMESTAMP,
    days_before_expiry INTEGER,
    consumption_reason VARCHAR(50)
);
```

---

## 🤖 **Machine Learning Features**

### **Real ML Algorithms**
- ✅ **K-Nearest Neighbors (KNN)** - Pattern recognition
- ✅ **Naïve Bayes** - Probabilistic classification
- ✅ **Decision Tree** - Rule-based predictions
- ✅ **Random Forest** - Ensemble learning
- ✅ **K-Means Clustering** - Item grouping

### **ML Features**
- **Personalized Predictions**: Learns from your consumption patterns
- **Consumption Forecasting**: Predicts when you'll eat items
- **Smart Clustering**: Groups similar items automatically
- **Priority Scoring**: Real algorithm for consumption order
- **Pattern Recognition**: Discovers your habits over time

### **How ML Works**
1. **Data Collection**: Tracks your consumption history
2. **Feature Extraction**: Analyzes patterns, seasons, timing
3. **Model Training**: Trains on your personal data
4. **Prediction**: Forecasts future consumption
5. **Improvement**: Gets smarter with more data

---

## 📊 **API Endpoints**

### **Authentication**
- `POST /register` - User registration
- `POST /login` - User login

### **Inventory Management**
- `GET /items` - Get all items
- `POST /add` - Add new item
- `PUT /update/<id>` - Update item
- `DELETE /delete/<id>` - Delete item

### **ML Features**
- `POST /train-models` - Train ML models for user
- `POST /predict-consumption` - Get consumption predictions
- `GET /analytics` - Get clustering and trends
- `GET /risk-heatmap` - Get expiry risk analysis

### **Dashboard**
- `GET /dashboard` - Get dashboard metrics

---

## 🔧 **Key Improvements**

### **Database Benefits**
- ✅ **Persistent Storage**: Data survives server restarts
- ✅ **Multi-User**: Each user has isolated data
- ✅ **Relationships**: Proper data relationships
- ✅ **Queries**: Complex data analysis possible
- ✅ **Scalability**: Handles thousands of records

### **ML Benefits**
- ✅ **Real Learning**: Improves with more data
- ✅ **Personalization**: Tailored to each user
- ✅ **Accuracy**: Based on actual patterns
- ✅ **Insights**: Discovers hidden patterns
- ✅ **Forecasting**: Predicts future behavior

---

## 🎯 **Usage Examples**

### **Add Item with Real ML**
```json
POST /add
{
    "name": "Organic Milk",
    "category": "Dairy",
    "quantity": 1,
    "quantity_unit": "liters",
    "expiry": "2024-06-25",
    "has_expiry": true
}
```

### **Train ML Models**
```bash
curl -X POST http://localhost:5000/train-models
```

### **Get Real Predictions**
```json
POST /predict-consumption
{
    "items": [
        {"name": "Milk", "days_left": 5, "quantity": 1}
    ]
}
```

**Response:**
```json
{
    "predictions": [
        {
            "item_name": "Milk",
            "knn_prediction": 0.82,
            "nb_prediction": 0.78,
            "dt_prediction": 0.85,
            "rf_prediction": 0.80,
            "ensemble_prediction": 0.81
        }
    ]
}
```

---

## 📈 **Performance Benefits**

### **Speed**
- **Database**: SQLite is fast for this scale
- **ML**: Models trained per user (small datasets)
- **API**: Optimized queries with indexes

### **Scalability**
- **Users**: Supports unlimited users
- **Items**: Each user can have thousands of items
- **History**: Tracks consumption over months/years

### **Reliability**
- **ACID Compliance**: Data integrity guaranteed
- **Error Handling**: Robust error management
- **Backup**: Easy database backup/restore

---

## 🔒 **Security Features**

### **Authentication**
- **Password Hashing**: bcrypt for secure storage
- **Session Management**: Secure user sessions
- **Input Validation**: Prevents SQL injection

### **Data Protection**
- **User Isolation**: Each user sees only their data
- **Input Sanitization**: Clean data input
- **Error Messages**: No sensitive data exposure

---

## 🚀 **Future Enhancements**

### **Database Upgrades**
- **PostgreSQL**: For larger scale
- **Redis**: For caching
- **Backup**: Automated backups

### **ML Enhancements**
- **Deep Learning**: TensorFlow/PyTorch models
- **Computer Vision**: Real freshness detection
- **Time Series**: Advanced forecasting
- **Recommendations**: Collaborative filtering

### **Features**
- **Mobile App**: React Native
- **API**: RESTful with documentation
- **Monitoring**: Performance metrics
- **Testing**: Automated test suite

---

## 🎉 **Ready for Production!**

Your Smart Fridge AI now has:
- ✅ **Real database** with persistent storage
- ✅ **Machine learning** that learns from users
- ✅ **Multi-user support** for households
- ✅ **Scalable architecture** for growth
- ✅ **Production-ready** security and performance

**Start using real ML + database today!** 🚀
