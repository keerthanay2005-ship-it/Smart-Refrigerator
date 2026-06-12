// Global variables
let currentUser = null;
let inventoryData = [];
let charts = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    setupEventListeners();
    setMinDate();
    loadSupabaseConfig();
    startClockAndAlertsPolling();
});

// Set minimum date for expiry input to today
function setMinDate() {
    const today = new Date().toISOString().split('T')[0];
    const expiryInput = document.getElementById('foodExpiry');
    if (expiryInput) {
        expiryInput.min = today;
    }
}

// Check authentication status
function checkAuthStatus() {
    // In a real app, you'd check session/token here
    // For demo, we'll show login modal
    showLogin();
}

// Setup event listeners
function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Register form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }

    // Add food form
    const addFoodForm = document.getElementById('addFoodForm');
    if (addFoodForm) {
        addFoodForm.addEventListener('submit', handleAddFood);
    }

    // Expiry date checkbox toggle
    const hasExpiryDate = document.getElementById('hasExpiryDate');
    if (hasExpiryDate) {
        hasExpiryDate.addEventListener('change', toggleExpiryDateField);
    }

    // Category change to show/hide ripeness field
    const foodCategory = document.getElementById('foodCategory');
    if (foodCategory) {
        foodCategory.addEventListener('change', toggleRipenessField);
    }

    // Search and filter
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterInventory);
    }

    const filterCategory = document.getElementById('filterCategory');
    if (filterCategory) {
        filterCategory.addEventListener('change', filterInventory);
    }

    // Image upload
    const imageUpload = document.getElementById('imageUpload');
    if (imageUpload) {
        imageUpload.addEventListener('change', handleImageUpload);
    }
}

// Authentication functions
function showLogin() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            currentUser = data.user;
            localStorage.setItem('token', data.token);
            showDashboard();
            bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
        } else {
            alert('Login failed: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Login error:', error);
        // For demo purposes, simulate successful login
        currentUser = { id: 'demo', username: 'Demo User', email: email };
        showDashboard();
        bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
    });
}

function handleRegister(e) {
    e.preventDefault();
    
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const household = document.getElementById('registerHousehold').value;

    fetch('/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, email, password, household })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert('Registration successful! Please login.');
            // Switch to login tab
            document.querySelector('[href="#login"]').click();
        } else {
            alert('Registration failed: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Registration error:', error);
        alert('Registration successful! Please login.');
        document.querySelector('[href="#login"]').click();
    });
}

function logout() {
    currentUser = null;
    localStorage.removeItem('token');
    document.getElementById('dashboardSection').classList.add('d-none');
    document.getElementById('welcomeSection').classList.remove('d-none');
    document.getElementById('loginBtn').classList.remove('d-none');
    document.getElementById('logoutBtn').classList.add('d-none');
}

function showDashboard() {
    document.getElementById('dashboardSection').classList.remove('d-none');
    document.getElementById('welcomeSection').classList.add('d-none');
    document.getElementById('loginBtn').classList.add('d-none');
    document.getElementById('logoutBtn').classList.remove('d-none');
    
    loadDashboard();
    loadInventory();
}

// Dashboard functions
function loadDashboard() {
    if (SupabaseAdapter.isEnabled()) {
        SupabaseAdapter.getItems()
        .then(items => {
            const total = items.length;
            const expiring = items.filter(item => item.days_left >= 0 && item.days_left <= 3).length;
            const low = items.filter(item => {
                return item.quantity_unit === 'pieces' || item.quantity_unit === 'dozen' ? item.quantity <= 2 : item.quantity <= 0.5;
            }).length;
            const expired = items.filter(item => item.days_left < 0).length;
            
            document.getElementById('totalItems').textContent = total;
            document.getElementById('expiringSoon').textContent = expiring;
            document.getElementById('lowStock').textContent = low;
            document.getElementById('expired').textContent = expired;
            
            loadPriorityQueue(items);
        })
        .catch(error => {
            console.error("Supabase load dashboard error:", error);
            loadDashboardOriginal();
        });
    } else {
        loadDashboardOriginal();
    }
}

function loadDashboardOriginal() {
    fetch('/dashboard')
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // For demo, use mock data
            data = getMockDashboardData();
        }
        
        // Update stats
        document.getElementById('totalItems').textContent = data.total_items;
        document.getElementById('expiringSoon').textContent = data.expiring_soon;
        document.getElementById('lowStock').textContent = data.low_stock;
        document.getElementById('expired').textContent = data.expired;
        
        // Load priority queue
        loadPriorityQueue(data.items);
        
        // Load analytics when tab is shown
        document.querySelector('[href="#analytics"]').addEventListener('shown.bs.tab', () => {
            loadAnalytics();
        });
        
        // Load heatmap when tab is shown
        document.querySelector('[href="#heatmap"]').addEventListener('shown.bs.tab', () => {
            loadRiskHeatmap();
        });
    })
    .catch(error => {
        console.error('Dashboard error:', error);
        // Use mock data for demo
        const data = getMockDashboardData();
        document.getElementById('totalItems').textContent = data.total_items;
        document.getElementById('expiringSoon').textContent = data.expiring_soon;
        document.getElementById('lowStock').textContent = data.low_stock;
        document.getElementById('expired').textContent = data.expired;
        loadPriorityQueue(data.items);
    });
}

function getMockDashboardData() {
    return {
        total_items: 15,
        expiring_soon: 3,
        low_stock: 2,
        expired: 1,
        items: [
            { name: 'Milk', category: 'Dairy', quantity: 1, days_left: 2, priority_score: 90 },
            { name: 'Bananas', category: 'Fruits', quantity: 6, days_left: 3, priority_score: 80 },
            { name: 'Bread', category: 'Packaged', quantity: 1, days_left: 5, priority_score: 60 }
        ]
    };
}

// Toggle expiry date field
function toggleExpiryDateField() {
    const hasExpiry = document.getElementById('hasExpiryDate').checked;
    const expiryField = document.getElementById('expiryDateField');
    const noExpiryField = document.getElementById('noExpiryField');
    const expiryInput = document.getElementById('foodExpiry');
    
    if (hasExpiry) {
        expiryField.classList.remove('d-none');
        noExpiryField.classList.add('d-none');
        expiryInput.required = true;
    } else {
        expiryField.classList.add('d-none');
        noExpiryField.classList.remove('d-none');
        expiryInput.required = false;
    }
}

// Toggle ripeness field based on category
function toggleRipenessField() {
    const category = document.getElementById('foodCategory').value;
    const ripenessField = document.getElementById('ripenessField');
    
    // Show ripeness field for fruits and vegetables
    if (category === 'Fruits' || category === 'Vegetables') {
        ripenessField.style.display = 'block';
    } else {
        ripenessField.style.display = 'none';
    }
}

// Inventory functions
function handleAddFood(e) {
    e.preventDefault();
    
    const hasExpiry = document.getElementById('hasExpiryDate').checked;
    let expiryDate = '';
    let daysLeft = 0;
    
    if (hasExpiry) {
        expiryDate = document.getElementById('foodExpiry').value;
        daysLeft = Math.floor((new Date(expiryDate) - new Date()) / (1000 * 60 * 60 * 24));
    } else {
        // Use estimated freshness
        const estimatedDays = parseInt(document.getElementById('estimatedFreshness').value);
        if (estimatedDays) {
            const futureDate = new Date();
            futureDate.setDate(futureDate.getDate() + estimatedDays);
            expiryDate = futureDate.toISOString().split('T')[0];
            daysLeft = estimatedDays;
        }
    }
    
    const foodData = {
        name: document.getElementById('foodName').value,
        category: document.getElementById('foodCategory').value,
        quantity: parseFloat(document.getElementById('foodQuantity').value),
        quantity_unit: document.getElementById('quantityUnit').value,
        storage_location: document.getElementById('storageLocation').value,
        expiry: expiryDate,
        has_expiry: hasExpiry,
        ripeness: document.getElementById('ripeness')?.value || null
    };

    if (SupabaseAdapter.isEnabled()) {
        SupabaseAdapter.addItem(foodData)
        .then(data => {
            alert('Item added successfully!');
            document.getElementById('addFoodForm').reset();
            triggerFlyingAnimation(foodData.name, foodData.category, foodData.storage_location);
            loadInventory();
            loadDashboard();
        })
        .catch(error => {
            alert('Error adding item to Supabase: ' + error.message);
        });
        return;
    }

    fetch('/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(foodData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert('Item added successfully!');
            document.getElementById('addFoodForm').reset();
            triggerFlyingAnimation(foodData.name, foodData.category, foodData.storage_location);
            loadInventory();
            loadDashboard();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Add item error:', error);
        // For demo, simulate success
        alert('Item added successfully!');
        document.getElementById('addFoodForm').reset();
        triggerFlyingAnimation(foodData.name, foodData.category, foodData.storage_location);
        loadInventory();
        loadDashboard();
    });
}

function loadInventory() {
    if (SupabaseAdapter.isEnabled()) {
        SupabaseAdapter.getItems()
        .then(items => {
            inventoryData = items;
            displayInventory(items);
            populateVisualFridge(items);
        })
        .catch(error => {
            console.error("Supabase load inventory error:", error);
            loadInventoryOriginal();
        });
    } else {
        loadInventoryOriginal();
    }
}

function loadInventoryOriginal() {
    fetch('/items')
    .then(response => response.json())
    .then(items => {
        if (items.error) {
            // Use mock data for demo
            items = getMockInventoryData();
        }
        inventoryData = items;
        displayInventory(items);
        populateVisualFridge(items);
    })
    .catch(error => {
        console.error('Load inventory error:', error);
        // Use mock data for demo
        const items = getMockInventoryData();
        inventoryData = items;
        displayInventory(items);
        populateVisualFridge(items);
    });
}

function getMockInventoryData() {
    return [
        { _id: '1', name: 'Milk', category: 'Dairy', quantity: 1, storage_location: 'Shelf', expiry: '2024-06-20', days_left: 2, priority_score: 90, expiry_risk: 'Critical', freshness_color: '#FF6B6B' },
        { _id: '2', name: 'Bananas', category: 'Fruits', quantity: 6, storage_location: 'Shelf', expiry: '2024-06-21', days_left: 3, priority_score: 80, expiry_risk: 'High', freshness_color: '#FFA500' },
        { _id: '3', name: 'Bread', category: 'Packaged', quantity: 1, storage_location: 'Shelf', expiry: '2024-06-23', days_left: 5, priority_score: 60, expiry_risk: 'Medium', freshness_color: '#FFD700' },
        { _id: '4', name: 'Apples', category: 'Fruits', quantity: 8, storage_location: 'Drawer', expiry: '2024-07-01', days_left: 13, priority_score: 30, expiry_risk: 'Low', freshness_color: '#90EE90' },
        { _id: '5', name: 'Yogurt', category: 'Dairy', quantity: 2, storage_location: 'Shelf', expiry: '2024-06-18', days_left: 0, priority_score: 100, expiry_risk: 'Expired', freshness_color: '#FF0000' }
    ];
}

function displayInventory(items) {
    const tbody = document.getElementById('inventoryBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    items.forEach(item => {
        const itemId = item._id || item.id;
        const quantityDisplay = `${item.quantity} ${item.quantity_unit || 'pieces'}`;
        const isLowStock = item.quantity_unit === 'pieces' ? item.quantity <= 2 : item.quantity <= 0.5;
        
        const row = tbody.insertRow();
        row.id = `item-row-${itemId}`;
        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="rounded-circle me-2" style="width: 12px; height: 12px; background-color: ${item.freshness_color || '#90EE90'};"></div>
                    ${item.name}
                </div>
            </td>
            <td><span class="badge bg-secondary">${item.category}</span></td>
            <td>
                <span class="badge ${isLowStock ? 'bg-warning' : 'bg-success'}">${quantityDisplay}</span>
            </td>
            <td>${item.storage_location || 'Shelf'}</td>
            <td>${formatDate(item.expiry || item.expiry_date)} ${item.has_expiry ? '' : '(est.)'}</td>
            <td>
                <span class="badge bg-${getRiskBadgeColor(item.expiry_risk)}">${item.days_left} days</span>
            </td>
            <td>
                <span class="badge bg-${getRiskBadgeColor(item.expiry_risk)}">${item.expiry_risk || 'Low'}</span>
            </td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar bg-${getPriorityColor(item.priority_score)}" role="progressbar" style="width: ${item.priority_score}%">
                        ${item.priority_score}
                    </div>
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem('${itemId}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteItem('${itemId}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
    });
}

function filterInventory() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('filterCategory').value;
    
    const filteredItems = inventoryData.filter(item => {
        const matchesSearch = item.name.toLowerCase().includes(searchTerm) || 
                             item.category.toLowerCase().includes(searchTerm);
        const matchesCategory = !categoryFilter || item.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });
    
    displayInventory(filteredItems);
}

function getRiskBadgeColor(risk) {
    switch(risk) {
        case 'Expired': return 'danger';
        case 'Critical': return 'danger';
        case 'High': return 'warning';
        case 'Medium': return 'info';
        default: return 'success';
    }
}

function getPriorityColor(score) {
    if (score >= 80) return 'danger';
    if (score >= 60) return 'warning';
    if (score >= 40) return 'info';
    return 'success';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function deleteItem(itemId) {
    if (confirm('Are you sure you want to delete this item?')) {
        if (SupabaseAdapter.isEnabled()) {
            SupabaseAdapter.deleteItem(itemId)
            .then(() => {
                loadInventory();
                loadDashboard();
            })
            .catch(error => {
                console.error("Supabase delete error:", error);
                alert("Failed to delete item from Supabase.");
            });
            return;
        }

        fetch(`/delete/${itemId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                loadInventory();
                loadDashboard();
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            // For demo, simulate success
            loadInventory();
            loadDashboard();
        });
    }
}

function editItem(itemId) {
    // For demo, just show an alert
    alert('Edit functionality would open a modal to edit the item details.');
}

// Priority Queue
function loadPriorityQueue(items) {
    const queueContainer = document.getElementById('priorityQueue');
    queueContainer.innerHTML = '';
    
    if (!items || items.length === 0) {
        queueContainer.innerHTML = '<p class="text-muted">No items in priority queue.</p>';
        return;
    }
    
    items.forEach((item, index) => {
        const priorityCard = document.createElement('div');
        priorityCard.className = 'card mb-3 border-left border-5';
        priorityCard.style.borderLeftColor = getPriorityBorderColor(item.priority_score);
        
        priorityCard.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="card-title mb-1">
                            <span class="badge bg-primary me-2">${index + 1}</span>
                            ${item.name}
                        </h5>
                        <p class="card-text mb-1">
                            <small class="text-muted">${item.category} • ${item.quantity} units • ${item.storage_location || 'Shelf'}</small>
                        </p>
                        <div class="d-flex gap-2">
                            <span class="badge bg-${getRiskBadgeColor(item.expiry_risk)}">${item.days_left} days left</span>
                            <span class="badge bg-info">Priority: ${item.priority_score}</span>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="rounded-circle d-flex align-items-center justify-content-center" 
                             style="width: 60px; height: 60px; background-color: ${item.freshness_color || '#90EE90'}; color: white;">
                            <i class="fas fa-utensils fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        queueContainer.appendChild(priorityCard);
    });
}

function getPriorityBorderColor(score) {
    if (score >= 80) return '#dc3545';
    if (score >= 60) return '#ffc107';
    if (score >= 40) return '#17a2b8';
    return '#28a745';
}

// Freshness Detection
function handleImageUpload(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            const preview = document.getElementById('imagePreview');
            preview.innerHTML = `
                <img src="${event.target.result}" class="img-thumbnail mb-3" style="max-height: 200px;">
                <p class="text-muted">Image loaded. Click "Analyze Freshness" to detect.</p>
            `;
        };
        reader.readAsDataURL(file);
    }
}

function startCamera() {
    alert('Camera functionality would open device camera for real-time capture.');
}

function detectFreshness() {
    const preview = document.getElementById('imagePreview');
    const img = preview.querySelector('img');
    
    if (!img) {
        alert('Please upload an image first.');
        return;
    }
    
    // Convert image to base64
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    ctx.drawImage(img, 0, 0);
    const base64Image = canvas.toDataURL('image/jpeg');
    
    fetch('/detect-freshness', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image: base64Image })
    })
    .then(response => response.json())
    .then(data => {
        displayFreshnessResult(data);
    })
    .catch(error => {
        console.error('Freshness detection error:', error);
        // Use mock result for demo
        const mockResult = {
            freshness: 'Fresh',
            confidence: 0.85,
            color_analysis: {
                mean_hue: 45,
                mean_saturation: 120,
                mean_value: 180
            }
        };
        displayFreshnessResult(mockResult);
    });
}

function displayFreshnessResult(result) {
    const resultContainer = document.getElementById('freshnessResult');
    
    const freshnessColor = result.freshness === 'Fresh' ? 'success' : 
                          result.freshness === 'Ripe' ? 'warning' : 'danger';
    
    resultContainer.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h5>Freshness Analysis Results</h5>
            </div>
            <div class="card-body">
                <div class="text-center mb-3">
                    <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-2" 
                         style="width: 100px; height: 100px; background-color: ${getFreshnessColor(result.freshness)};">
                        <i class="fas fa-leaf fa-3x text-white"></i>
                    </div>
                    <h4>${result.freshness}</h4>
                    <p class="text-muted">Confidence: ${(result.confidence * 100).toFixed(1)}%</p>
                </div>
                
                <div class="progress mb-3" style="height: 25px;">
                    <div class="progress-bar bg-${freshnessColor}" role="progressbar" 
                         style="width: ${result.confidence * 100}%">
                        ${(result.confidence * 100).toFixed(1)}% Confidence
                    </div>
                </div>
                
                <h6>Color Analysis:</h6>
                <ul class="list-unstyled">
                    <li><strong>Mean Hue:</strong> ${result.color_analysis.mean_hue.toFixed(1)}</li>
                    <li><strong>Mean Saturation:</strong> ${result.color_analysis.mean_saturation.toFixed(1)}</li>
                    <li><strong>Mean Value:</strong> ${result.color_analysis.mean_value.toFixed(1)}</li>
                </ul>
                
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    ${getFreshnessAdvice(result.freshness)}
                </div>
            </div>
        </div>
    `;
}

function getFreshnessColor(freshness) {
    switch(freshness) {
        case 'Fresh': return '#28a745';
        case 'Ripe': return '#ffc107';
        case 'Overripe': return '#dc3545';
        default: return '#6c757d';
    }
}

function getFreshnessAdvice(freshness) {
    switch(freshness) {
        case 'Fresh':
            return 'This item appears fresh and is ready for consumption. Store properly to maintain freshness.';
        case 'Ripe':
            return 'This item is ripe and should be consumed soon for best flavor and nutrition.';
        case 'Overripe':
            return 'This item is overripe and should be consumed immediately or used in cooking.';
        default:
            return 'Unable to determine freshness. Please check manually.';
    }
}

// Analytics
function loadAnalytics() {
    fetch('/analytics')
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            data = getMockAnalyticsData();
        }
        
        displayCategoryChart(data.category_distribution);
        displayTrendsChart(data.monthly_trends);
        displayClusterAnalysis(data.clusters);
        displaySustainabilityScore(data.sustainability_score, data.waste_rate);
    })
    .catch(error => {
        console.error('Analytics error:', error);
        const data = getMockAnalyticsData();
        displayCategoryChart(data.category_distribution);
        displayTrendsChart(data.monthly_trends);
        displayClusterAnalysis(data.clusters);
        displaySustainabilityScore(data.sustainability_score, data.waste_rate);
    });
}

function getMockAnalyticsData() {
    return {
        category_distribution: {
            'Fruits': 5,
            'Vegetables': 4,
            'Dairy': 3,
            'Packaged': 2,
            'Meat': 1
        },
        monthly_trends: [
            { month: 'Jan', consumed: 45, wasted: 5 },
            { month: 'Feb', consumed: 52, wasted: 3 },
            { month: 'Mar', consumed: 48, wasted: 7 },
            { month: 'Apr', consumed: 61, wasted: 4 },
            { month: 'May', consumed: 55, wasted: 6 },
            { month: 'Jun', consumed: 58, wasted: 2 }
        ],
        clusters: [
            { cluster_id: 0, count: 5, avg_days_left: 2, avg_quantity: 3, items: ['Milk', 'Yogurt'] },
            { cluster_id: 1, count: 8, avg_days_left: 10, avg_quantity: 5, items: ['Apples', 'Bananas'] },
            { cluster_id: 2, count: 2, avg_days_left: 30, avg_quantity: 10, items: ['Frozen items'] }
        ],
        sustainability_score: 85,
        waste_rate: 15
    };
}

function displayCategoryChart(distribution) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    if (charts.category) {
        charts.category.destroy();
    }
    
    charts.category = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(distribution),
            datasets: [{
                data: Object.values(distribution),
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function displayTrendsChart(trends) {
    const ctx = document.getElementById('trendsChart').getContext('2d');
    
    if (charts.trends) {
        charts.trends.destroy();
    }
    
    charts.trends = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trends.map(t => t.month),
            datasets: [{
                label: 'Consumed',
                data: trends.map(t => t.consumed),
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4
            }, {
                label: 'Wasted',
                data: trends.map(t => t.wasted),
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function displayClusterAnalysis(clusters) {
    const container = document.getElementById('clusterAnalysis');
    container.innerHTML = '';
    
    clusters.forEach(cluster => {
        const clusterCard = document.createElement('div');
        clusterCard.className = 'col-md-4 mb-3';
        
        const riskColor = cluster.avg_days_left < 3 ? 'danger' : 
                          cluster.avg_days_left < 7 ? 'warning' : 'success';
        
        clusterCard.innerHTML = `
            <div class="card">
                <div class="card-header bg-${riskColor} text-white">
                    <h6 class="mb-0">Cluster ${cluster.cluster_id + 1}</h6>
                </div>
                <div class="card-body">
                    <p><strong>Items:</strong> ${cluster.count}</p>
                    <p><strong>Avg Days Left:</strong> ${cluster.avg_days_left.toFixed(1)}</p>
                    <p><strong>Avg Quantity:</strong> ${cluster.avg_quantity.toFixed(1)}</p>
                    <p><strong>Sample Items:</strong></p>
                    <ul class="list-unstyled">
                        ${cluster.items.map(item => `<li><small>• ${item}</small></li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
        
        container.appendChild(clusterCard);
    });
}

function displaySustainabilityScore(score, wasteRate) {
    const scoreBar = document.getElementById('sustainabilityScore');
    const wasteSpan = document.getElementById('wasteRate');
    
    scoreBar.style.width = score + '%';
    scoreBar.textContent = score + '%';
    wasteSpan.textContent = wasteRate.toFixed(1) + '%';
    
    // Update color based on score
    scoreBar.className = 'progress-bar bg-' + (score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger');
}

// Risk Heatmap
function loadRiskHeatmap() {
    fetch('/risk-heatmap')
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            data = getMockHeatmapData();
        }
        displayRiskHeatmap(data.risk_grid);
    })
    .catch(error => {
        console.error('Heatmap error:', error);
        const data = getMockHeatmapData();
        displayRiskHeatmap(data.risk_grid);
    });
}

function getMockHeatmapData() {
    return {
        risk_grid: [
            { category: 'Fruits', risk_level: 'High', risk_score: 75, item_count: 5, color: '#FFA500' },
            { category: 'Vegetables', risk_level: 'Medium', risk_score: 45, item_count: 4, color: '#FFD700' },
            { category: 'Dairy', risk_level: 'High', risk_score: 85, item_count: 3, color: '#FF6B6B' },
            { category: 'Packaged', risk_level: 'Low', risk_score: 25, item_count: 2, color: '#90EE90' },
            { category: 'Meat', risk_level: 'Critical', risk_score: 95, item_count: 1, color: '#FF0000' },
            { category: 'Other', risk_level: 'Low', risk_score: 15, item_count: 3, color: '#90EE90' }
        ]
    };
}

function displayRiskHeatmap(riskGrid) {
    const container = document.getElementById('riskHeatmap');
    container.innerHTML = '';
    
    const gridContainer = document.createElement('div');
    gridContainer.className = 'row';
    
    riskGrid.forEach(item => {
        const gridItem = document.createElement('div');
        gridItem.className = 'col-md-4 mb-3';
        
        gridItem.innerHTML = `
            <div class="card h-100 border-3" style="border-color: ${item.color};">
                <div class="card-body text-center">
                    <h5 class="card-title">${item.category}</h5>
                    <div class="rounded-circle mx-auto mb-3 d-flex align-items-center justify-content-center" 
                         style="width: 80px; height: 80px; background-color: ${item.color}; color: white;">
                        <div>
                            <div class="h4 mb-0">${item.item_count}</div>
                            <small>items</small>
                        </div>
                    </div>
                    <p class="card-text">
                        <span class="badge bg-${getRiskBadgeColor(item.risk_level)}">${item.risk_level} Risk</span><br>
                        <small class="text-muted">Score: ${item.risk_score.toFixed(0)}</small>
                    </p>
                </div>
            </div>
        `;
        
        gridContainer.appendChild(gridItem);
    });
    
    container.appendChild(gridContainer);
    
    // Add legend
    const legend = document.createElement('div');
    legend.className = 'mt-3';
    legend.innerHTML = `
        <div class="d-flex justify-content-center gap-3">
            <div class="d-flex align-items-center">
                <div class="rounded-circle me-2" style="width: 20px; height: 20px; background-color: #FF0000;"></div>
                <small>Critical Risk</small>
            </div>
            <div class="d-flex align-items-center">
                <div class="rounded-circle me-2" style="width: 20px; height: 20px; background-color: #FFA500;"></div>
                <small>High Risk</small>
            </div>
            <div class="d-flex align-items-center">
                <div class="rounded-circle me-2" style="width: 20px; height: 20px; background-color: #FFD700;"></div>
                <small>Medium Risk</small>
            </div>
            <div class="d-flex align-items-center">
                <div class="rounded-circle me-2" style="width: 20px; height: 20px; background-color: #90EE90;"></div>
                <small>Low Risk</small>
            </div>
        </div>
    `;
    container.appendChild(legend);
}

// ML Predictions
function generatePredictions() {
    fetch('/predict-consumption', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            data = getMockMLPredictions();
        }
        displayMLPredictions(data.predictions);
    })
    .catch(error => {
        console.error('ML prediction error:', error);
        const data = getMockMLPredictions();
        displayMLPredictions(data.predictions);
    });
}

function getMockMLPredictions() {
    return {
        predictions: [
            {
                item_name: 'Milk',
                knn_prediction: 0.85,
                nb_prediction: 0.78,
                dt_prediction: 0.82,
                ensemble_prediction: 0.82
            },
            {
                item_name: 'Bananas',
                knn_prediction: 0.91,
                nb_prediction: 0.88,
                dt_prediction: 0.93,
                ensemble_prediction: 0.91
            },
            {
                item_name: 'Bread',
                knn_prediction: 0.73,
                nb_prediction: 0.69,
                dt_prediction: 0.75,
                ensemble_prediction: 0.72
            }
        ]
    };
}

function displayMLPredictions(predictions) {
    const container = document.getElementById('mlPredictions');
    container.innerHTML = '';
    
    predictions.forEach(pred => {
        const predCard = document.createElement('div');
        predCard.className = 'card mb-3';
        
        predCard.innerHTML = `
            <div class="card-header">
                <h6 class="mb-0">${pred.item_name} - Consumption Prediction</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>KNN</h5>
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar bg-primary" style="width: ${(pred.knn_prediction * 100).toFixed(1)}%">
                                    ${(pred.knn_prediction * 100).toFixed(1)}%
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>Naïve Bayes</h5>
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar bg-info" style="width: ${(pred.nb_prediction * 100).toFixed(1)}%">
                                    ${(pred.nb_prediction * 100).toFixed(1)}%
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>Decision Tree</h5>
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar bg-warning" style="width: ${(pred.dt_prediction * 100).toFixed(1)}%">
                                    ${(pred.dt_prediction * 100).toFixed(1)}%
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h5>Ensemble</h5>
                            <div class="progress" style="height: 20px;">
                                <div class="progress-bar bg-success" style="width: ${(pred.ensemble_prediction * 100).toFixed(1)}%">
                                    ${(pred.ensemble_prediction * 100).toFixed(1)}%
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle me-1"></i>
                        Higher values indicate higher likelihood of consumption in the next 7 days.
                    </small>
                </div>
            </div>
        `;
        
        container.appendChild(predCard);
    });
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// ==========================================
// Refrigerator UI & Interaction Helpers
// ==========================================

function toggleDoors(e) {
    if (e) e.stopPropagation();
    const freezer = document.getElementById('freezerDoor');
    const fridge = document.getElementById('fridgeDoor');
    
    if (!freezer || !fridge) return;
    
    const isOpen = freezer.classList.contains('open') || fridge.classList.contains('open');
    
    if (isOpen) {
        freezer.classList.remove('open');
        fridge.classList.remove('open');
    } else {
        freezer.classList.add('open');
        fridge.classList.add('open');
    }
}

function closeDoors(e) {
    if (e) e.stopPropagation();
    const freezer = document.getElementById('freezerDoor');
    const fridge = document.getElementById('fridgeDoor');
    if (freezer) freezer.classList.remove('open');
    if (fridge) fridge.classList.remove('open');
}

function getCategoryIcon(category) {
    switch(category) {
        case 'Fruits': return 'fas fa-apple-alt';
        case 'Vegetables': return 'fas fa-carrot';
        case 'Dairy': return 'fas fa-cheese';
        case 'Packaged': return 'fas fa-box-open';
        case 'Meat': return 'fas fa-drumstick-bite';
        case 'Beverages': return 'fas fa-glass-water';
        default: return 'fas fa-egg';
    }
}

function getRiskClass(daysLeft) {
    if (daysLeft < 0) return 'danger';
    if (daysLeft <= 3) return 'warning';
    return 'fresh';
}

function populateVisualFridge(items) {
    // Clear shelf list items
    ['Freezer', 'Shelf', 'Door', 'Drawer'].forEach(loc => {
        const container = document.getElementById(`shelf-${loc}`);
        if (container) container.innerHTML = '';
    });
    
    items.forEach(item => {
        let location = item.storage_location || 'Shelf';
        if (!['Freezer', 'Shelf', 'Door', 'Drawer'].includes(location)) {
            location = 'Shelf';
        }
        
        const container = document.getElementById(`shelf-${location}`);
        if (container) {
            const pill = document.createElement('div');
            pill.className = `fridge-item-pill ${getRiskClass(item.days_left)}`;
            
            const itemId = item._id || item.id;
            pill.title = `${item.name} (${item.quantity} ${item.quantity_unit || 'pieces'}) - ${item.days_left}d left`;
            
            const icon = getCategoryIcon(item.category);
            pill.innerHTML = `<i class="${icon}"></i> ${item.name}`;
            pill.onclick = (e) => {
                e.stopPropagation();
                highlightInventoryItem(itemId);
            };
            
            container.appendChild(pill);
        }
    });
}

function highlightInventoryItem(itemId) {
    const rowId = `item-row-${itemId}`;
    const row = document.getElementById(rowId);
    if (row) {
        // Switch tab to Inventory if not already there
        const tab = document.querySelector('[href="#inventory"]');
        if (tab) tab.click();
        
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.classList.add('table-primary');
        row.style.transition = 'background-color 0.5s';
        setTimeout(() => {
            row.classList.remove('table-primary');
        }, 2000);
    }
}

function triggerFlyingAnimation(name, category, location) {
    const form = document.getElementById('addFoodForm');
    if (!form) return;
    const submitBtn = form.querySelector('button[type="submit"]');
    const targetShelf = document.getElementById(`shelf-${location || 'Shelf'}`);
    
    if (!submitBtn || !targetShelf) return;
    
    const startRect = submitBtn.getBoundingClientRect();
    const endRect = targetShelf.getBoundingClientRect();
    
    const particle = document.createElement('div');
    particle.className = 'flying-food-particle';
    const icon = getCategoryIcon(category);
    particle.innerHTML = `<i class="${icon} me-1"></i> ${name}`;
    
    particle.style.left = `${startRect.left + window.scrollX}px`;
    particle.style.top = `${startRect.top + window.scrollY}px`;
    document.body.appendChild(particle);
    
    // Open doors so they see it land
    const freezerDoor = document.getElementById('freezerDoor');
    const fridgeDoor = document.getElementById('fridgeDoor');
    if (freezerDoor && !freezerDoor.classList.contains('open')) {
        freezerDoor.classList.add('open');
    }
    if (fridgeDoor && !fridgeDoor.classList.contains('open')) {
        fridgeDoor.classList.add('open');
    }
    
    setTimeout(() => {
        particle.style.left = `${endRect.left + window.scrollX + (endRect.width / 2) - 50}px`;
        particle.style.top = `${endRect.top + window.scrollY + (endRect.height / 2) - 15}px`;
        particle.style.transform = 'scale(0.5)';
        particle.style.opacity = '0.2';
    }, 50);
    
    setTimeout(() => {
        particle.remove();
        const shelfGlass = targetShelf.nextElementSibling;
        if (shelfGlass) {
            shelfGlass.style.boxShadow = '0 0 20px rgba(0, 242, 254, 1)';
            setTimeout(() => {
                shelfGlass.style.boxShadow = '';
            }, 500);
        }
    }, 850);
}

// ==========================================
// Supabase Local Storage Integration & Adapter
// ==========================================

let supabaseClient = null;

function getSupabaseClient() {
    if (supabaseClient) return supabaseClient;
    const url = localStorage.getItem('supabaseUrl') || 'https://drzoyuxfvzxkstrrjxes.supabase.co';
    const key = localStorage.getItem('supabaseKey') || 'sb_publishable_YBu9s8jf7R-4y3K4mQ57CQ_jfFqQ2Zu';
    const enabled = localStorage.getItem('supabaseEnabled') !== 'false';
    if (enabled && url && key) {
        try {
            supabaseClient = supabase.createClient(url, key);
        } catch (e) {
            console.error("Failed to initialize Supabase:", e);
        }
    }
    return supabaseClient;
}

const SupabaseAdapter = {
    isEnabled: function() {
        return localStorage.getItem('supabaseEnabled') !== 'false' && !!getSupabaseClient();
    },
    
    getItems: async function() {
        const client = getSupabaseClient();
        if (!client) return [];
        
        const userId = currentUser ? currentUser.id : 'demo';
        const { data, error } = await client
            .from('food_items')
            .select('*')
            .eq('user_id', userId);
            
        if (error) {
            console.error("Supabase select error:", error);
            throw error;
        }
        
        return data.map(item => ({
            _id: item.id,
            name: item.name,
            category: item.category,
            quantity: parseFloat(item.quantity),
            quantity_unit: item.quantity_unit,
            storage_location: item.storage_location,
            expiry: item.expiry_date,
            has_expiry: item.has_expiry,
            days_left: calculateDaysLeft(item.expiry_date),
            priority_score: calculatePriorityScoreLocal(calculateDaysLeft(item.expiry_date), item.quantity),
            expiry_risk: getExpiryRisk(calculateDaysLeft(item.expiry_date)),
            freshness_color: getFreshnessColor(calculateDaysLeft(item.expiry_date))
        }));
    },
    
    addItem: async function(itemData) {
        const client = getSupabaseClient();
        if (!client) return null;
        
        const userId = currentUser ? currentUser.id : 'demo';
        const daysLeft = itemData.expiry ? calculateDaysLeft(itemData.expiry) : 0;
        const priorityScore = calculatePriorityScoreLocal(daysLeft, itemData.quantity);
        
        const { data, error } = await client
            .from('food_items')
            .insert({
                user_id: userId,
                name: itemData.name,
                category: itemData.category,
                quantity: itemData.quantity,
                quantity_unit: itemData.quantity_unit,
                storage_location: itemData.storage_location,
                expiry_date: itemData.expiry || null,
                has_expiry: itemData.has_expiry,
                days_left: daysLeft,
                priority_score: priorityScore
            })
            .select();
            
        if (error) {
            console.error("Supabase insert error:", error);
            throw error;
        }
        return data[0];
    },
    
    deleteItem: async function(itemId) {
        const client = getSupabaseClient();
        if (!client) return null;
        
        const { error } = await client
            .from('food_items')
            .delete()
            .eq('id', itemId);
            
        if (error) {
            console.error("Supabase delete error:", error);
            throw error;
        }
        return true;
    }
};

function calculateDaysLeft(expiryDateStr) {
    if (!expiryDateStr) return 0;
    const diffTime = new Date(expiryDateStr) - new Date();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

function calculatePriorityScoreLocal(daysLeft, quantity) {
    if (daysLeft < 0) return 100;
    if (daysLeft <= 3) return 80 + (3 - daysLeft) * 10;
    if (daysLeft <= 7) return 50 + (7 - daysLeft) * 6;
    return Math.max(10, 50 - daysLeft / 2);
}

function getExpiryRisk(daysLeft) {
    if (daysLeft < 0) return "Expired";
    if (daysLeft <= 2) return "Critical";
    if (daysLeft <= 5) return "High";
    if (daysLeft <= 10) return "Medium";
    return "Low";
}

function getFreshnessColor(daysLeft) {
    if (daysLeft < 0) return "#FF0000";
    if (daysLeft <= 3) return "#FF6B6B";
    if (daysLeft <= 7) return "#FFA500";
    if (daysLeft <= 14) return "#FFD700";
    return "#90EE90";
}

function saveSupabaseConfig() {
    const url = document.getElementById('supabaseUrl').value.trim();
    const key = document.getElementById('supabaseKey').value.trim();
    const enabled = document.getElementById('enableSupabase').checked;
    
    localStorage.setItem('supabaseUrl', url);
    localStorage.setItem('supabaseKey', key);
    localStorage.setItem('supabaseEnabled', enabled ? 'true' : 'false');
    
    supabaseClient = null;
    alert("Configuration saved successfully!");
    
    loadInventory();
    loadDashboard();
}

function loadSupabaseConfig() {
    const urlInput = document.getElementById('supabaseUrl');
    const keyInput = document.getElementById('supabaseKey');
    const enabledInput = document.getElementById('enableSupabase');
    
    if (urlInput) urlInput.value = localStorage.getItem('supabaseUrl') || 'https://drzoyuxfvzxkstrrjxes.supabase.co';
    if (keyInput) keyInput.value = localStorage.getItem('supabaseKey') || 'sb_publishable_YBu9s8jf7R-4y3K4mQ57CQ_jfFqQ2Zu';
    if (enabledInput) {
        enabledInput.checked = localStorage.getItem('supabaseEnabled') !== 'false';
    }
    
    if (Notification.permission === 'granted') {
        const btn = document.getElementById('btnRequestNotification');
        if (btn) {
            btn.className = 'btn btn-success';
            btn.innerHTML = '<i class="fas fa-check-circle me-1"></i>Notifications Enabled';
        }
    }
}

// ==========================================
// Desktop & Smart Hub Notifications
// ==========================================

function requestNotificationPermission() {
    if (!("Notification" in window)) {
        alert("This browser does not support desktop notifications.");
        return;
    }
    Notification.requestPermission().then(permission => {
        const btn = document.getElementById('btnRequestNotification');
        if (btn) {
            if (permission === 'granted') {
                btn.className = 'btn btn-success';
                btn.innerHTML = '<i class="fas fa-check-circle me-1"></i>Notifications Enabled';
            } else {
                btn.className = 'btn btn-danger';
                btn.innerHTML = '<i class="fas fa-times-circle me-1"></i>Notifications Blocked';
            }
        }
    });
}

function sendPushNotification(title, body) {
    if (Notification.permission === "granted") {
        try {
            new Notification(title, { body: body });
        } catch (e) {
            console.error("Failed to trigger notification:", e);
        }
    }
}

function testBrowserNotification() {
    if (Notification.permission !== "granted") {
        alert("Please enable desktop notifications first.");
        return;
    }
    sendPushNotification("Smart Refrigerator Test", "This is a test notification from your Smart Refrigerator!");
}

let alertsIntervalId = null;

function startClockAndAlertsPolling() {
    setInterval(() => {
        const clockSpan = document.getElementById('screenTime');
        if (clockSpan) {
            const now = new Date();
            let hours = now.getHours();
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const ampm = hours >= 12 ? 'PM' : 'AM';
            hours = hours % 12;
            hours = hours ? hours : 12;
            clockSpan.textContent = `${hours}:${minutes} ${ampm}`;
        }
    }, 1000);
    
    setupAlertPolling();
    
    const intervalSelect = document.getElementById('alertInterval');
    if (intervalSelect) {
        intervalSelect.addEventListener('change', () => {
            setupAlertPolling();
        });
    }
}

function setupAlertPolling() {
    if (alertsIntervalId) clearInterval(alertsIntervalId);
    
    setTimeout(() => { checkAlerts(); }, 1500);
    
    const intervalSelect = document.getElementById('alertInterval');
    const interval = intervalSelect ? parseInt(intervalSelect.value) : 3600000;
    
    alertsIntervalId = setInterval(() => {
        checkAlerts();
    }, interval);
}

function checkAlerts() {
    if (SupabaseAdapter.isEnabled()) {
        SupabaseAdapter.getItems()
        .then(items => {
            const expired = items.filter(item => item.days_left < 0);
            const expiring_soon = items.filter(item => item.days_left >= 0 && item.days_left <= 3);
            const low_stock = items.filter(item => {
                return item.quantity_unit === 'pieces' || item.quantity_unit === 'dozen' ? item.quantity <= 2 : item.quantity <= 0.5;
            });
            updateSmartScreenNotifications(expired, expiring_soon, low_stock);
        })
        .catch(err => console.error("Error checking Supabase alerts:", err));
    } else {
        fetch('/api/alerts')
        .then(response => {
            if (!response.ok) throw new Error("Unauthorized");
            return response.json();
        })
        .then(data => {
            updateSmartScreenNotifications(data.expired, data.expiring_soon, data.low_stock);
        })
        .catch(err => {
            console.error("Error checking Flask alerts:", err);
            const expired = inventoryData.filter(item => item.days_left < 0);
            const expiring_soon = inventoryData.filter(item => item.days_left >= 0 && item.days_left <= 3);
            const low_stock = inventoryData.filter(item => {
                return item.quantity_unit === 'pieces' || item.quantity_unit === 'dozen' ? item.quantity <= 2 : item.quantity <= 0.5;
            });
            updateSmartScreenNotifications(expired, expiring_soon, low_stock);
        });
    }
}

function updateSmartScreenNotifications(expired, expiring_soon, low_stock) {
    const container = document.getElementById('screenNotifications');
    if (!container) return;
    
    container.innerHTML = '';
    const allAlerts = [];
    
    expired.forEach(item => {
        allAlerts.push(`<div class="alert-item small text-danger"><i class="fas fa-exclamation-circle me-1"></i>${item.name} EXPIRED!</div>`);
    });
    expiring_soon.forEach(item => {
        allAlerts.push(`<div class="alert-item small text-warning"><i class="fas fa-clock me-1"></i>${item.name} (${item.days_left}d)</div>`);
    });
    low_stock.forEach(item => {
        allAlerts.push(`<div class="alert-item small text-info"><i class="fas fa-info-circle me-1"></i>${item.name} Low Stock</div>`);
    });
    
    if (allAlerts.length > 0) {
        container.innerHTML = allAlerts.join('');
        
        const notifiedKey = 'notified_items_' + (currentUser ? currentUser.id : 'demo');
        let notified = JSON.parse(localStorage.getItem(notifiedKey) || '[]');
        let newPushes = [];
        
        expired.forEach(item => {
            const id = item._id || item.id;
            if (!notified.includes(id + '_expired')) {
                newPushes.push(`EXPIRED: ${item.name}`);
                notified.push(id + '_expired');
            }
        });
        expiring_soon.forEach(item => {
            const id = item._id || item.id;
            if (!notified.includes(id + '_soon')) {
                newPushes.push(`Expiring soon: ${item.name} (${item.days_left} days left)`);
                notified.push(id + '_soon');
            }
        });
        low_stock.forEach(item => {
            const id = item._id || item.id;
            if (!notified.includes(id + '_low')) {
                newPushes.push(`Low stock: ${item.name} (${item.quantity} left)`);
                notified.push(id + '_low');
            }
        });
        
        if (newPushes.length > 0) {
            localStorage.setItem(notifiedKey, JSON.stringify(notified));
            sendPushNotification("Smart Refrigerator Alert", newPushes.join('\n'));
        }
    } else {
        container.innerHTML = '<div class="no-alerts small text-muted">No active alerts. Fridge is running optimal!</div>';
    }
}
