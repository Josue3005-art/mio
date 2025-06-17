// WebSocket connection for real-time updates
let socket;
let isConnected = false;

// Chart instances
let balanceChart;
let profitChart;

// Dashboard state
let dashboardData = {
    balance: 0,
    dailyProfit: 0,
    totalTrades: 0,
    successRate: 0
};

// Initialize dashboard when DOM is loaded
function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // Initialize WebSocket connection
    initializeWebSocket();
    
    // Initialize auto-refresh
    setInterval(refreshDashboardData, 30000); // Refresh every 30 seconds
    
    // Initialize UI event handlers
    initializeEventHandlers();
    
    console.log('Dashboard initialized successfully');
}

// Initialize WebSocket connection
function initializeWebSocket() {
    try {
        socket = io();
        
        socket.on('connect', function() {
            console.log('Connected to WebSocket');
            isConnected = true;
            updateConnectionStatus(true);
            
            // Request initial data
            socket.emit('get_balance');
            socket.emit('get_recent_trades');
            socket.emit('get_alerts');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from WebSocket');
            isConnected = false;
            updateConnectionStatus(false);
        });
        
        socket.on('connect_error', function(error) {
            console.error('WebSocket connection error:', error);
            isConnected = false;
            updateConnectionStatus(false);
        });
        
        // Handle real-time updates
        socket.on('balance_update', handleBalanceUpdate);
        socket.on('trade_executed', handleTradeExecuted);
        socket.on('new_alert', handleNewAlert);
        socket.on('opportunity_detected', handleOpportunityDetected);
        socket.on('system_status', handleSystemStatus);
        socket.on('trades_update', handleTradesUpdate);
        socket.on('alerts_update', handleAlertsUpdate);
        
    } catch (error) {
        console.error('Error initializing WebSocket:', error);
        updateConnectionStatus(false);
    }
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (statusIndicator && statusText) {
        if (connected) {
            statusIndicator.className = 'fas fa-circle text-success me-1';
            statusText.textContent = 'Connected';
        } else {
            statusIndicator.className = 'fas fa-circle text-danger me-1';
            statusText.textContent = 'Disconnected';
        }
    }
}

// Handle balance updates
function handleBalanceUpdate(data) {
    console.log('Balance update received:', data);
    
    try {
        // Update total balance display
        const totalBalanceElement = document.getElementById('totalBalance');
        if (totalBalanceElement && data.total_usd !== undefined) {
            totalBalanceElement.textContent = `$${data.total_usd.toFixed(2)}`;
            dashboardData.balance = data.total_usd;
        }
        
        // Update balance breakdown
        if (data.balances) {
            updateBalanceBreakdown(data.balances);
        }
        
        // Add visual feedback
        animateUpdate(totalBalanceElement);
        
    } catch (error) {
        console.error('Error handling balance update:', error);
    }
}

// Handle trade execution notifications
function handleTradeExecuted(data) {
    console.log('Trade executed:', data);
    
    try {
        // Show notification
        showTradeNotification(data.trade);
        
        // Update trades table
        if (socket && isConnected) {
            socket.emit('get_recent_trades');
        }
        
        // Update statistics
        updateTradingStats();
        
    } catch (error) {
        console.error('Error handling trade execution:', error);
    }
}

// Handle new alerts
function handleNewAlert(data) {
    console.log('New alert received:', data);
    
    try {
        // Add alert to alerts container
        addAlertToContainer(data);
        
        // Show browser notification if supported
        showBrowserNotification(data.title, data.message);
        
    } catch (error) {
        console.error('Error handling new alert:', error);
    }
}

// Handle opportunity detection
function handleOpportunityDetected(data) {
    console.log('Opportunity detected:', data);
    
    try {
        // Update opportunities table
        updateOpportunitiesTable(data.opportunity);
        
        // Show notification for high-profit opportunities
        if (data.opportunity.potential_profit > 1.0) {
            showOpportunityNotification(data.opportunity);
        }
        
    } catch (error) {
        console.error('Error handling opportunity detection:', error);
    }
}

// Handle system status updates
function handleSystemStatus(data) {
    console.log('System status update:', data);
    
    try {
        // Update system status display
        updateSystemStatus(data.status, data.message);
        
    } catch (error) {
        console.error('Error handling system status:', error);
    }
}

// Handle trades table updates
function handleTradesUpdate(data) {
    console.log('Trades update received:', data);
    
    try {
        updateTradesTable(data.trades);
    } catch (error) {
        console.error('Error handling trades update:', error);
    }
}

// Handle alerts table updates
function handleAlertsUpdate(data) {
    console.log('Alerts update received:', data);
    
    try {
        updateAlertsContainer(data.alerts);
    } catch (error) {
        console.error('Error handling alerts update:', error);
    }
}

// Update balance breakdown display
function updateBalanceBreakdown(balances) {
    const container = document.getElementById('balanceBreakdown');
    if (!container) return;
    
    container.innerHTML = '';
    
    balances.forEach(balance => {
        if (balance.total > 0) {
            const balanceItem = document.createElement('div');
            balanceItem.className = 'd-flex justify-content-between align-items-center mb-2';
            balanceItem.innerHTML = `
                <div>
                    <strong>${balance.asset}</strong>
                    <div class="text-muted small">${balance.total.toFixed(6)}</div>
                </div>
                <div class="text-end">
                    <div>$${balance.usd_value.toFixed(2)}</div>
                </div>
            `;
            container.appendChild(balanceItem);
        }
    });
}

// Update trades table
function updateTradesTable(trades) {
    const tbody = document.getElementById('tradesTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        const profitClass = trade.profit_loss > 0 ? 'text-success' : 
                           trade.profit_loss < 0 ? 'text-danger' : 'text-muted';
        
        row.innerHTML = `
            <td>${trade.executed_at}</td>
            <td><code>${trade.symbol}</code></td>
            <td>
                <span class="badge bg-${trade.side === 'BUY' ? 'success' : 'danger'}">
                    ${trade.side}
                </span>
            </td>
            <td>$${trade.total_value.toFixed(2)}</td>
            <td>${trade.price.toFixed(6)}</td>
            <td class="${profitClass}">
                ${trade.profit_loss ? `$${trade.profit_loss.toFixed(2)}` : '-'}
            </td>
            <td>
                <span class="badge bg-secondary">${trade.strategy}</span>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Update alerts container
function updateAlertsContainer(alerts) {
    const container = document.getElementById('alertsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="text-muted text-center">No new alerts</div>';
        return;
    }
    
    alerts.forEach(alert => {
        addAlertToContainer(alert);
    });
}

// Add single alert to container
function addAlertToContainer(alert) {
    const container = document.getElementById('alertsContainer');
    if (!container) return;
    
    // Remove "no alerts" message if present
    const noAlertsMsg = container.querySelector('.text-muted.text-center');
    if (noAlertsMsg) {
        noAlertsMsg.remove();
    }
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${alert.type.toLowerCase()} alert-sm`;
    alertElement.innerHTML = `
        <strong>${alert.title}</strong><br>
        <small>${alert.message}</small>
        <div class="text-muted small">${alert.created_at || new Date().toLocaleTimeString()}</div>
    `;
    
    // Add to top of container
    container.insertBefore(alertElement, container.firstChild);
    
    // Remove old alerts if more than 5
    const alerts = container.querySelectorAll('.alert');
    if (alerts.length > 5) {
        alerts[alerts.length - 1].remove();
    }
}

// Show trade notification
function showTradeNotification(trade) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    const emoji = trade.side === 'BUY' ? '🟢' : '🔴';
    notification.innerHTML = `
        ${emoji} <strong>Trade ${trade.side}</strong><br>
        Symbol: <code>${trade.symbol}</code><br>
        Amount: $${trade.total_value?.toFixed(2) || 'N/A'}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Show opportunity notification
function showOpportunityNotification(opportunity) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-warning alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        🎯 <strong>High Profit Opportunity</strong><br>
        Symbol: <code>${opportunity.symbol}</code><br>
        Potential: $${opportunity.potential_profit.toFixed(2)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 8000);
}

// Show browser notification
function showBrowserNotification(title, message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/favicon.ico'
        });
    } else if ('Notification' in window && Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                new Notification(title, {
                    body: message,
                    icon: '/static/favicon.ico'
                });
            }
        });
    }
}

// Animate element update
function animateUpdate(element) {
    if (!element) return;
    
    element.style.transform = 'scale(1.05)';
    element.style.transition = 'transform 0.2s ease';
    
    setTimeout(() => {
        element.style.transform = 'scale(1)';
    }, 200);
}

// Refresh dashboard data manually
function refreshDashboardData() {
    if (socket && isConnected) {
        socket.emit('get_balance');
        socket.emit('get_recent_trades');
        socket.emit('get_alerts');
    } else {
        // Fallback to API calls if WebSocket is not available
        fetchDashboardDataFromAPI();
    }
}

// Fetch data from API as fallback
async function fetchDashboardDataFromAPI() {
    try {
        // Fetch balance
        const balanceResponse = await fetch('/api/balance');
        if (balanceResponse.ok) {
            const balanceData = await balanceResponse.json();
            if (balanceData.success) {
                handleBalanceUpdate(balanceData);
            }
        }
        
        // Fetch recent trades
        const tradesResponse = await fetch('/api/trades?limit=10');
        if (tradesResponse.ok) {
            const tradesData = await tradesResponse.json();
            if (tradesData.success) {
                updateTradesTable(tradesData.trades);
            }
        }
        
    } catch (error) {
        console.error('Error fetching dashboard data from API:', error);
    }
}

// Refresh trades table
function refreshTrades() {
    if (socket && isConnected) {
        socket.emit('get_recent_trades');
    } else {
        fetchDashboardDataFromAPI();
    }
    
    // Visual feedback
    const button = event.target;
    const originalIcon = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    setTimeout(() => {
        button.innerHTML = originalIcon;
    }, 1000);
}

// Manual arbitrage scan
async function scanArbitrage() {
    const scanBtn = document.getElementById('scanBtn');
    const originalContent = scanBtn.innerHTML;
    
    // Show loading state
    scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
    scanBtn.disabled = true;
    
    try {
        const response = await fetch('/api/scan_arbitrage', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success notification
            showBrowserNotification('Arbitrage Scan', data.message);
            
            // Refresh data after scan
            setTimeout(() => {
                refreshDashboardData();
            }, 1000);
        } else {
            console.error('Scan failed:', data.error);
            showBrowserNotification('Scan Error', 'Failed to complete arbitrage scan');
        }
        
    } catch (error) {
        console.error('Error during arbitrage scan:', error);
        showBrowserNotification('Scan Error', 'Network error during scan');
    } finally {
        // Restore button state
        scanBtn.innerHTML = originalContent;
        scanBtn.disabled = false;
    }
}

// Mark all alerts as read
async function markAlertsRead() {
    try {
        const response = await fetch('/api/alerts/mark_read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const container = document.getElementById('alertsContainer');
            if (container) {
                container.innerHTML = '<div class="text-muted text-center">No new alerts</div>';
            }
        }
        
    } catch (error) {
        console.error('Error marking alerts as read:', error);
    }
}

// Update trading statistics
function updateTradingStats() {
    // This could fetch and update real-time statistics
    // For now, we'll rely on page refresh or WebSocket updates
}

// Update system status
function updateSystemStatus(status, message) {
    // Could update a system status indicator
    console.log(`System status: ${status} - ${message}`);
}

// Update opportunities table
function updateOpportunitiesTable(opportunity) {
    const tbody = document.getElementById('opportunitiesTableBody');
    if (!tbody) return;
    
    // Create new row for the opportunity
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><code>${opportunity.symbol}</code></td>
        <td>${opportunity.buy_price.toFixed(6)}</td>
        <td>${opportunity.sell_price.toFixed(6)}</td>
        <td>
            <span class="badge bg-info">${(opportunity.spread_percentage * 100).toFixed(2)}%</span>
        </td>
        <td class="text-success">$${opportunity.potential_profit.toFixed(2)}</td>
        <td>
            <span class="badge bg-warning">DETECTED</span>
        </td>
        <td>${new Date().toLocaleTimeString()}</td>
    `;
    
    // Add to top of table
    tbody.insertBefore(row, tbody.firstChild);
    
    // Remove old rows if more than 10
    const rows = tbody.querySelectorAll('tr');
    if (rows.length > 10) {
        rows[rows.length - 1].remove();
    }
}

// Initialize event handlers
function initializeEventHandlers() {
    // Request notification permissions on load
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Handle visibility change to refresh when tab becomes active
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && isConnected) {
            refreshDashboardData();
        }
    });
    
    // Handle window focus to refresh data
    window.addEventListener('focus', function() {
        if (isConnected) {
            refreshDashboardData();
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+R or F5 - Refresh data
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            refreshDashboardData();
        }
    });
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('Dashboard error:', e.error);
});

// Unhandled promise rejection handling
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});

// Export functions for global access
window.refreshTrades = refreshTrades;
window.markAlertsRead = markAlertsRead;
window.initializeDashboard = initializeDashboard;
