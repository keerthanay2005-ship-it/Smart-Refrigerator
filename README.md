# Smart Refrigerator AI - Intelligent Food Management System

A comprehensive AI-powered food inventory management system that helps reduce waste, optimize consumption, and provide intelligent insights about your food storage.

## 🌟 Features

### 1. User Management
- **User Registration & Login**: Secure authentication system
- **Multi-user Household Support**: Share inventory with family members
- **Profile Customization**: Personalized preferences and settings
- **Consumption History Tracking**: Monitor usage patterns over time

### 2. Smart Dashboard
- **Summary View**: Total food items at a glance
- **Expiry Alerts**: Items expiring soon highlighted
- **Low-stock Overview**: Never run out of essentials
- **Priority-based Ranking**: Smart consumption suggestions
- **Visual Indicators**: Color-coded expiry risks

### 3. Food Inventory Management
- **CRUD Operations**: Add, edit, delete food items
- **Categorization**: Fruits, Vegetables, Dairy, Packaged, Meat, Other
- **Quantity Tracking**: Monitor stock levels
- **Storage Location**: Shelf, Drawer, Freezer, Door tracking
- **Search & Filter**: Find items quickly
- **Real-time Updates**: Live inventory dashboard

### 4. Expiry Date Tracking
- **Manual Entry**: Easy date input
- **Automatic Calculation**: Days remaining computed
- **Color-coded Indicators**: Visual expiry warnings
- **Expiry History**: Track patterns over time
- **Archive System**: Manage expired items

### 5. Smart Consumption Priority Index
- **Priority Algorithm**: `f(days_left, quantity, usage_frequency)`
- **Automatic Ranking**: Items sorted by consumption priority
- **Waste Risk Identification**: High-risk items highlighted
- **Priority-based Sorting**: Consume what's most urgent first

### 6. Freshness Detection (Computer Vision)
- **Image Upload**: Upload photos of food items
- **Camera Capture**: Real-time image analysis
- **AI Classification**: Fruit and vegetable identification
- **Condition Detection**: Raw, Ripe, Over-ripe, Spoiled
- **Confidence Scoring**: Reliability metrics
- **Visual Indicators**: Freshness status display

### 7. Machine Learning Features
- **KNN Classification**: K-Nearest Neighbors algorithm
- **Naïve Bayes**: Probabilistic classification
- **Decision Tree**: Rule-based predictions
- **Consumption Prediction**: Forecast usage patterns
- **Personalized Reminders**: AI-driven notifications
- **Pattern Recognition**: Learn from purchase history

### 8. Clustering and Analytics
- **K-Means Clustering**: Group similar items
- **Frequently Used Items**: Identify consumption patterns
- **Waste Analysis**: Track commonly wasted items
- **Usage Trends**: Monthly consumption reports
- **Time Series Forecasting**: Predict future needs
- **Sustainability Metrics**: Environmental impact tracking

### 9. Notification System
- **Expiry Reminders**: Timely alerts
- **Near-expiry Warnings**: Early notifications
- **Spoilage Alerts**: Quality deterioration warnings
- **Low-stock Notifications**: Replenishment reminders
- **In-app Alerts**: Real-time updates

### 10. Expiry Risk Heatmap
- **Color-coded Grid**: Visual risk assessment
- **Red = High Risk**: Critical attention needed
- **Yellow = Moderate Risk**: Monitor closely
- **Green = Safe**: No immediate action needed
- **Category Distribution**: Risk by food type

### 11. Dashboard Visualizations
- **Inventory Overview**: Comprehensive food view
- **Expiry Timeline**: Time-based visualization
- **Consumption Statistics**: Usage analytics
- **Waste Reduction Metrics**: Progress tracking
- **Category Distribution Charts**: Visual breakdowns
- **Sustainability Score**: Environmental impact indicator

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB (local or cloud instance)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smart-fridge-ai
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MongoDB**
   - Install MongoDB locally or use MongoDB Atlas
   - Update the MongoDB URI in `app.py` if needed:
   ```python
   app.config["MONGO_URI"] = "mongodb://localhost:27017/smartfridge"
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## 📁 Project Structure

```
smart-fridge-ai/
├── app.py                 # Flask backend with all API endpoints
├── index.html            # Modern frontend with Bootstrap 5
├── script.js             # Comprehensive JavaScript functionality
├── style.css             # Enhanced CSS with animations
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🛠️ Technology Stack

### Backend
- **Flask**: Web framework
- **MongoDB**: NoSQL database
- **Flask-PyMongo**: MongoDB integration
- **Scikit-learn**: Machine learning algorithms
- **OpenCV**: Computer vision
- **TensorFlow**: Deep learning capabilities
- **NumPy/Pandas**: Data processing

### Frontend
- **Bootstrap 5**: Modern UI framework
- **Chart.js**: Data visualization
- **Font Awesome**: Icons
- **Vanilla JavaScript**: No additional frameworks needed

### Machine Learning
- **KNN**: K-Nearest Neighbors for classification
- **Naïve Bayes**: Probabilistic predictions
- **Decision Trees**: Rule-based learning
- **K-Means**: Clustering algorithm
- **Computer Vision**: Image analysis with OpenCV

## 📊 API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /login` - User login

### Dashboard
- `GET /dashboard` - Dashboard metrics and summary

### Inventory Management
- `POST /add` - Add new food item
- `GET /items` - Get all inventory items
- `PUT /update/<item_id>` - Update item details
- `DELETE /delete/<item_id>` - Delete item

### AI Features
- `POST /detect-freshness` - Analyze food freshness
- `POST /predict-consumption` - ML consumption predictions
- `GET /analytics` - Comprehensive analytics
- `GET /risk-heatmap` - Expiry risk visualization

## 🎯 Usage Guide

### 1. Getting Started
1. Register for a new account or login
2. Navigate to the dashboard to see overview
3. Add your first food items using the form

### 2. Adding Items
1. Fill in the food details (name, category, quantity, expiry)
2. Select storage location
3. Set expiry date
4. Click "Add Item"

### 3. Managing Inventory
1. View all items in the inventory table
2. Use search and filter to find specific items
3. Edit or delete items as needed
4. Monitor priority scores for consumption guidance

### 4. Using AI Features
1. **Freshness Detection**: Upload images for analysis
2. **ML Predictions**: Generate consumption forecasts
3. **Analytics**: View comprehensive insights
4. **Risk Heatmap**: Monitor expiry risks by category

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
MONGO_URI=mongodb://localhost:27017/smartfridge
```

### Customization
- Modify categories in the frontend dropdown
- Adjust priority algorithm in `calculate_priority_score()`
- Customize ML model parameters
- Update color schemes in CSS variables

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 Development Notes

### Priority Score Algorithm
The priority score is calculated using:
```python
def calculate_priority_score(item):
    days_left = item.get('days_left', 0)
    quantity = item.get('quantity', 1)
    usage_freq = item.get('usage_frequency', 1)
    
    if days_left < 0:
        return 100  # Expired items get highest priority
    elif days_left <= 3:
        return 80 + (3 - days_left) * 10
    elif days_left <= 7:
        return 50 + (7 - days_left) * 6
    else:
        return max(10, 50 - days_left / 2)
```

### Freshness Detection
The computer vision system analyzes:
- Color saturation and brightness
- Hue distribution
- Texture patterns
- Historical data comparison

### ML Model Training
Models are trained on:
- Historical consumption data
- User behavior patterns
- Seasonal variations
- Category-specific trends

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Ensure MongoDB is running
   - Check connection string in `app.py`
   - Verify network connectivity

2. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Check Python version compatibility

3. **Image Upload Issues**
   - Ensure file size limits
   - Check supported formats (JPG, PNG)
   - Verify browser permissions

4. **ML Model Errors**
   - Ensure sufficient training data
   - Check feature preprocessing
   - Verify model initialization

## 📈 Performance Optimization

### Database Indexing
Add indexes for frequently queried fields:
```javascript
db.food.createIndex({ "user_id": 1, "expiry": 1 })
db.food.createIndex({ "user_id": 1, "category": 1 })
```

### Caching Strategy
- Implement Redis for session management
- Cache ML model predictions
- Store analytics results temporarily

## 🔒 Security Considerations

- Password hashing with bcrypt
- JWT token authentication
- Input validation and sanitization
- Rate limiting for API endpoints
- Secure file upload handling

## 📱 Mobile Compatibility

The application is fully responsive and works on:
- iOS devices (iPhone, iPad)
- Android devices (phones, tablets)
- Progressive Web App (PWA) support

## 🌍 Internationalization

Ready for multi-language support:
- UTF-8 encoding
- Localized date formats
- Currency support (if needed)
- Time zone handling

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Submit an issue on GitHub
4. Contact the development team

## 🎉 Future Enhancements

Planned features:
- Mobile app (React Native)
- IoT device integration
- Recipe suggestions
- Shopping list generation
- Barcode scanning
- Voice commands
- Smart home integration
- Advanced analytics dashboard

---

**Smart Fridge AI** - Reducing food waste through intelligent technology 🥗🤖
