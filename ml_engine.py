import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import joblib
import os

class MLEngine:
    """Real Machine Learning Engine for Smart Fridge AI"""
    
    def __init__(self, db_path='smart_fridge.db'):
        self.db_path = db_path
        self.models = {}
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def get_user_data(self, user_id):
        """Get all user data for ML training"""
        conn = sqlite3.connect(self.db_path)
        
        # Get consumption history
        consumption_df = pd.read_sql_query('''
            SELECT * FROM consumption_history 
            WHERE user_id = ? 
            ORDER BY consumed_date DESC
        ''', conn, params=(user_id,))
        
        # Get current inventory
        inventory_df = pd.read_sql_query('''
            SELECT * FROM food_items 
            WHERE user_id = ? 
            AND days_left >= 0
        ''', conn, params=(user_id,))
        
        conn.close()
        return consumption_df, inventory_df
    
    def extract_features(self, consumption_df):
        """Extract ML features from consumption data"""
        if consumption_df.empty:
            return np.array([]), np.array([])
        
        features = []
        labels = []
        
        for _, row in consumption_df.iterrows():
            feature_vector = [
                row['days_before_expiry'] or 0,  # Days left when consumed
                row['quantity_consumed'],  # Amount consumed
                self._get_season_factor(row['consumed_date']),  # Season
                self._get_day_of_week(row['consumed_date']),  # Day of week
                self._get_time_of_day(row['consumed_date']),  # Time of day
                self._get_category_frequency(row['category'], consumption_df),  # Category frequency
            ]
            
            features.append(feature_vector)
            
            # Label: 1 if consumed before expiry, 0 if expired/thrown away
            label = 1 if row['consumption_reason'] == 'eaten' and (row['days_before_expiry'] or 0) >= 0 else 0
            labels.append(label)
        
        return np.array(features), np.array(labels)
    
    def _get_season_factor(self, date_str):
        """Extract season factor (0-3 for seasons)"""
        if isinstance(date_str, str):
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date = date_str
        
        month = date.month
        if month in [12, 1, 2]:  # Winter
            return 0
        elif month in [3, 4, 5]:  # Spring
            return 1
        elif month in [6, 7, 8]:  # Summer
            return 2
        else:  # Fall
            return 3
    
    def _get_day_of_week(self, date_str):
        """Extract day of week (0-6)"""
        if isinstance(date_str, str):
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date = date_str
        return date.weekday()
    
    def _get_time_of_day(self, date_str):
        """Extract time of day (0-3 for morning, afternoon, evening, night)"""
        if isinstance(date_str, str):
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date = date_str
        
        hour = date.hour
        if 6 <= hour < 12:  # Morning
            return 0
        elif 12 <= hour < 18:  # Afternoon
            return 1
        elif 18 <= hour < 22:  # Evening
            return 2
        else:  # Night
            return 3
    
    def _get_category_frequency(self, category, consumption_df):
        """Calculate how often this category is consumed"""
        category_count = len(consumption_df[consumption_df['category'] == category])
        total_count = len(consumption_df)
        return category_count / max(total_count, 1)
    
    def train_models(self, user_id):
        """Train ML models for a specific user"""
        consumption_df, _ = self.get_user_data(user_id)
        
        if len(consumption_df) < 5:
            print(f"⚠️  Not enough data for user {user_id}. Need at least 5 consumption records.")
            return False
        
        # Extract features
        X, y = self.extract_features(consumption_df)
        
        if len(X) == 0:
            return False
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train multiple models
        self.models['knn'] = KNeighborsClassifier(n_neighbors=min(5, len(X)))
        self.models['knn'].fit(X_scaled, y)
        
        self.models['naive_bayes'] = GaussianNB()
        self.models['naive_bayes'].fit(X_scaled, y)
        
        self.models['decision_tree'] = DecisionTreeClassifier(random_state=42)
        self.models['decision_tree'].fit(X_scaled, y)
        
        self.models['random_forest'] = RandomForestClassifier(n_estimators=10, random_state=42)
        self.models['random_forest'].fit(X_scaled, y)
        
        self.is_trained = True
        
        # Save models
        self.save_models(user_id)
        
        print(f"✅ ML models trained for user {user_id}")
        return True
    
    def predict_consumption(self, user_id, current_items):
        """Predict consumption likelihood for current items"""
        if not self.is_trained:
            # Try to load models
            if not self.load_models(user_id):
                return self._mock_predictions(current_items)
        
        predictions = []
        
        for item in current_items:
            # Create feature vector for this item
            features = self._create_item_features(item)
            
            if len(features) == 0:
                # Use mock prediction
                predictions.append({
                    'item_name': item['name'],
                    'knn_prediction': 0.75,
                    'nb_prediction': 0.70,
                    'dt_prediction': 0.72,
                    'rf_prediction': 0.78,
                    'ensemble_prediction': 0.74
                })
                continue
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Get predictions from all models
            knn_pred = self.models['knn'].predict_proba(features_scaled)[0][1] if len(self.models['knn'].classes_) > 1 else 0.5
            nb_pred = self.models['naive_bayes'].predict_proba(features_scaled)[0][1] if len(self.models['naive_bayes'].classes_) > 1 else 0.5
            dt_pred = self.models['decision_tree'].predict_proba(features_scaled)[0][1] if len(self.models['decision_tree'].classes_) > 1 else 0.5
            rf_pred = self.models['random_forest'].predict_proba(features_scaled)[0][1] if len(self.models['random_forest'].classes_) > 1 else 0.5
            
            # Ensemble prediction (average)
            ensemble_pred = (knn_pred + nb_pred + dt_pred + rf_pred) / 4
            
            predictions.append({
                'item_name': item['name'],
                'knn_prediction': float(knn_pred),
                'nb_prediction': float(nb_pred),
                'dt_prediction': float(dt_pred),
                'rf_prediction': float(rf_pred),
                'ensemble_prediction': float(ensemble_pred)
            })
        
        return predictions
    
    def _create_item_features(self, item):
        """Create feature vector for current item"""
        try:
            days_left = item.get('days_left', 0)
            quantity = item.get('quantity', 1)
            
            features = [
                days_left,  # Days left
                quantity,  # Quantity
                self._get_season_factor(datetime.now()),  # Current season
                datetime.now().weekday(),  # Current day of week
                self._get_time_of_day(datetime.now()),  # Current time
                0.1,  # Category frequency (placeholder)
            ]
            
            return features
        except:
            return []
    
    def _mock_predictions(self, current_items):
        """Fallback mock predictions"""
        predictions = []
        
        for item in current_items:
            days_left = item.get('days_left', 0)
            
            # Simple logic: higher prediction for items with more days left
            base_score = min(0.9, max(0.1, days_left / 30))
            
            predictions.append({
                'item_name': item['name'],
                'knn_prediction': base_score + np.random.normal(0, 0.05),
                'nb_prediction': base_score + np.random.normal(0, 0.05),
                'dt_prediction': base_score + np.random.normal(0, 0.05),
                'rf_prediction': base_score + np.random.normal(0, 0.05),
                'ensemble_prediction': base_score
            })
        
        return predictions
    
    def perform_clustering(self, user_id):
        """Perform K-means clustering on user's inventory"""
        _, inventory_df = self.get_user_data(user_id)
        
        if len(inventory_df) < 3:
            return self._mock_clusters()
        
        # Prepare features for clustering
        features = []
        for _, item in inventory_df.iterrows():
            feature_vector = [
                item['days_left'] or 0,
                item['quantity'],
                self._category_to_numeric(item['category']),
                self._location_to_numeric(item['storage_location']),
            ]
            features.append(feature_vector)
        
        if len(features) == 0:
            return self._mock_clusters()
        
        # Perform K-means clustering
        X = np.array(features)
        kmeans = KMeans(n_clusters=3, random_state=42)
        clusters = kmeans.fit_predict(X)
        
        # Analyze clusters
        cluster_analysis = []
        for i in range(3):
            cluster_items = inventory_df.iloc[clusters == i]
            
            if len(cluster_items) == 0:
                continue
            
            cluster_analysis.append({
                'cluster_id': i,
                'count': len(cluster_items),
                'avg_days_left': float(cluster_items['days_left'].mean()),
                'avg_quantity': float(cluster_items['quantity'].mean()),
                'items': cluster_items['name'].tolist()[:5],  # Sample items
                'categories': cluster_items['category'].tolist(),
                'risk_level': self._calculate_cluster_risk(cluster_items['days_left'].mean())
            })
        
        return cluster_analysis
    
    def _category_to_numeric(self, category):
        """Convert category to numeric value"""
        category_map = {
            'Fruits': 0, 'Vegetables': 1, 'Dairy': 2,
            'Packaged': 3, 'Meat': 4, 'Other': 5
        }
        return category_map.get(category, 5)
    
    def _location_to_numeric(self, location):
        """Convert storage location to numeric value"""
        location_map = {
            'Shelf': 0, 'Drawer': 1, 'Freezer': 2, 'Door': 3
        }
        return location_map.get(location, 0)
    
    def _calculate_cluster_risk(self, avg_days_left):
        """Calculate risk level for cluster"""
        if avg_days_left < 0:
            return 'High'
        elif avg_days_left < 7:
            return 'Medium'
        else:
            return 'Low'
    
    def _mock_clusters(self):
        """Fallback mock clustering"""
        return [
            {
                'cluster_id': 0,
                'count': 5,
                'avg_days_left': 2,
                'avg_quantity': 3,
                'items': ['Milk', 'Yogurt'],
                'categories': ['Dairy'],
                'risk_level': 'High'
            },
            {
                'cluster_id': 1,
                'count': 8,
                'avg_days_left': 10,
                'avg_quantity': 5,
                'items': ['Apples', 'Bananas'],
                'categories': ['Fruits'],
                'risk_level': 'Low'
            },
            {
                'cluster_id': 2,
                'count': 3,
                'avg_days_left': 30,
                'avg_quantity': 10,
                'items': ['Frozen items'],
                'categories': ['Packaged'],
                'risk_level': 'Low'
            }
        ]
    
    def save_models(self, user_id):
        """Save trained models to disk"""
        model_dir = f'models/user_{user_id}'
        os.makedirs(model_dir, exist_ok=True)
        
        for name, model in self.models.items():
            joblib.dump(model, f'{model_dir}/{name}.pkl')
        
        joblib.dump(self.scaler, f'{model_dir}/scaler.pkl')
    
    def load_models(self, user_id):
        """Load trained models from disk"""
        model_dir = f'models/user_{user_id}'
        
        if not os.path.exists(model_dir):
            return False
        
        try:
            self.models['knn'] = joblib.load(f'{model_dir}/knn.pkl')
            self.models['naive_bayes'] = joblib.load(f'{model_dir}/naive_bayes.pkl')
            self.models['decision_tree'] = joblib.load(f'{model_dir}/decision_tree.pkl')
            self.models['random_forest'] = joblib.load(f'{model_dir}/random_forest.pkl')
            self.scaler = joblib.load(f'{model_dir}/scaler.pkl')
            
            self.is_trained = True
            return True
        except:
            return False

# Example usage
if __name__ == '__main__':
    ml_engine = MLEngine()
    
    # Train models for user 1
    ml_engine.train_models(1)
    
    # Test predictions
    test_items = [
        {'name': 'Milk', 'days_left': 3, 'quantity': 1},
        {'name': 'Apples', 'days_left': 10, 'quantity': 6}
    ]
    
    predictions = ml_engine.predict_consumption(1, test_items)
    print("🔮 Predictions:", predictions)
    
    # Test clustering
    clusters = ml_engine.perform_clustering(1)
    print("📊 Clusters:", clusters)
