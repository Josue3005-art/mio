// Funciones del panel de administración optimizadas
function optimizeSystem() {
    if (!confirm('¿Ejecutar optimización completa del sistema?')) return;
    
    const btn = document.querySelector('.btn-success');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Optimizando...';
    
    fetch('/api/v2/performance/optimize', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: '{}'
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.success ? 'success' : 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
        if (data.success) {
            setTimeout(() => location.reload(), 2000);
        }
    })
    .catch(error => {
        showNotification('Error: ' + error.message, 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

function clearCache() {
    if (!confirm('¿Limpiar todo el cache del sistema?')) return;
    
    const btn = document.querySelector('.btn-warning');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Limpiando...';
    
    fetch('/api/v2/cache/clear', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: '{}'
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.success ? 'success' : 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    })
    .catch(error => {
        showNotification('Error: ' + error.message, 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
}

function refreshData() {
    const btn = document.querySelector('.btn-info');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Actualizando...';
    
    setTimeout(() => {
        location.reload();
    }, 1000);
}

function showNotification(message, type) {
    const alertClass = type === 'success' ? 'alert-success' : 
                     type === 'error' ? 'alert-danger' : 'alert-info';
    
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 350px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
            <div class="flex-grow-1">
                <strong>${type === 'success' ? 'Éxito' : type === 'error' ? 'Error' : 'Información'}:</strong><br>
                <small>${message}</small>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'bell';
}

// Funciones adicionales de administración
function makeAdmin(userId) {
    if (!confirm('¿Convertir este usuario en administrador?')) return;
    
    fetch('/admin/make_admin', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId})
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.success ? 'success' : 'error');
        if (data.success) {
            setTimeout(() => location.reload(), 2000);
        }
    });
}

function createLicense(userId) {
    document.getElementById('licenseUserId').value = userId;
    new bootstrap.Modal(document.getElementById('licenseModal')).show();
}

function generateCode(userId) {
    const customCode = prompt('Código personalizado (opcional):');
    
    fetch('/admin/generate_code', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId, custom_code: customCode})
    })
    .then(response => response.json())
    .then(data => showNotification(data.message, data.success ? 'success' : 'error'));
}

function submitLicense() {
    const userId = document.getElementById('licenseUserId').value;
    const planType = document.getElementById('licensePlanType').value;
    const duration = document.getElementById('licenseDuration').value;

    if (!userId.trim()) {
        showNotification('Por favor ingresa un ID de usuario válido', 'error');
        return;
    }

    fetch('/admin/create_license', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            user_id: userId,
            plan_type: planType,
            duration: parseInt(duration)
        })
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.success ? 'success' : 'error');
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('licenseModal')).hide();
            setTimeout(() => location.reload(), 2000);
        }
    });
}

// Sistema de monitoreo automático
function startHealthMonitoring() {
    setInterval(() => {
        fetch('/api/v2/system/health')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateSystemHealth(data.health_score, data.status);
                }
            })
            .catch(error => console.log('Health check failed:', error));
    }, 30000);
}

function updateSystemHealth(score, status) {
    const healthIndicator = document.querySelector('.badge.bg-warning');
    if (healthIndicator) {
        const colorClass = score > 80 ? 'bg-success' : score > 60 ? 'bg-warning' : 'bg-danger';
        healthIndicator.className = `badge ${colorClass} text-dark px-3 py-2`;
        healthIndicator.innerHTML = `<i class="fas fa-heart me-1"></i>Salud: ${score}%`;
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    console.log('Panel de administración cargado correctamente');
    startHealthMonitoring();
});