// Optimized dashboard for fast navigation
let dashboardData = {
    balance: 0,
    dailyProfit: 0,
    totalTrades: 0,
    successRate: 0
};

// Initialize dashboard quickly without WebSockets
function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // No WebSocket initialization
    updateConnectionStatus(true);
    
    // Initialize event handlers only
    initializeEventHandlers();
    
    console.log('Dashboard initialized successfully');
}

// Minimal event handlers
function initializeEventHandlers() {
    // Add click handlers for buttons if they exist
    const scanBtn = document.getElementById('scanBtn');
    if (scanBtn) {
        scanBtn.addEventListener('click', scanArbitrage);
    }
    
    const refreshBtn = document.querySelector('[onclick="refreshTrades()"]');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshTrades);
    }
}

// Simple connection status (always show connected)
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (statusIndicator && statusText) {
        statusIndicator.className = 'fas fa-circle text-success me-1';
        statusText.textContent = 'Connected';
    }
}

// Simplified arbitrage scan
async function scanArbitrage() {
    const scanBtn = document.getElementById('scanBtn');
    if (!scanBtn) return;
    
    const originalContent = scanBtn.innerHTML;
    scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
    scanBtn.disabled = true;
    
    try {
        const response = await fetch('/api/scan_arbitrage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Arbitrage scan completed successfully');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showNotification('Scan failed: ' + (data.error || 'Unknown error'));
        }
        
    } catch (error) {
        showNotification('Network error during scan');
    } finally {
        scanBtn.innerHTML = originalContent;
        scanBtn.disabled = false;
    }
}

// Simplified refresh trades
function refreshTrades() {
    window.location.reload();
}

// Simple notification system
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Export for global use
window.initializeDashboard = initializeDashboard;
window.scanArbitrage = scanArbitrage;
window.refreshTrades = refreshTrades;