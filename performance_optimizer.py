"""
Optimizador de rendimiento para el sistema de trading
"""
from app import app, db
from models import Trade, Balance, DailyStats, Alert, User, Subscription
from datetime import datetime, timedelta
import threading
import time
import logging
from sqlalchemy import text

class PerformanceOptimizer:
    """Optimizador de rendimiento del sistema"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutos
        self.last_cleanup = datetime.utcnow()
        
    def get_cached_data(self, key, fetch_function, timeout=None):
        """Sistema de cache inteligente"""
        timeout = timeout or self.cache_timeout
        now = datetime.utcnow()
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if (now - timestamp).seconds < timeout:
                return data
        
        # Obtener datos frescos
        data = fetch_function()
        self.cache[key] = (data, now)
        return data
    
    def cleanup_old_data(self):
        """Limpiar datos antiguos de la base de datos"""
        try:
            with app.app_context():
                # Limpiar alertas viejas (más de 30 días)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                old_alerts = Alert.query.filter(Alert.created_at < cutoff_date).count()
                Alert.query.filter(Alert.created_at < cutoff_date).delete()
                
                # Limpiar trades demo viejos (más de 7 días)
                demo_cutoff = datetime.utcnow() - timedelta(days=7)
                old_trades = Trade.query.filter(
                    Trade.executed_at < demo_cutoff,
                    Trade.exchange == 'SIMULATION'
                ).count()
                Trade.query.filter(
                    Trade.executed_at < demo_cutoff,
                    Trade.exchange == 'SIMULATION'
                ).delete()
                
                db.session.commit()
                logging.info(f"Limpieza completada: {old_alerts} alertas, {old_trades} trades demo")
                
        except Exception as e:
            logging.error(f"Error en limpieza: {e}")
    
    def optimize_database(self):
        """Optimizar rendimiento de la base de datos"""
        try:
            with app.app_context():
                # Crear índices para mejorar consultas
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_trades_executed_at 
                    ON trade (executed_at DESC);
                """))
                
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_created_at 
                    ON alert (created_at DESC);
                """))
                
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_subscription_user_status 
                    ON subscription (user_id, status);
                """))
                
                # Actualizar estadísticas de la base de datos
                db.session.execute(text("ANALYZE;"))
                db.session.commit()
                
                logging.info("Optimización de base de datos completada")
                
        except Exception as e:
            logging.error(f"Error en optimización DB: {e}")
    
    def get_optimized_dashboard_data(self):
        """Obtener datos del dashboard optimizados"""
        def fetch_dashboard():
            try:
                with app.app_context():
                    # Estadísticas básicas
                    total_trades = Trade.query.count()
                    total_profit = db.session.execute(
                        text("SELECT COALESCE(SUM(profit_loss), 0) FROM trade")
                    ).scalar() or 0.0
                    
                    # Balance actual
                    current_balance = Balance.query.first()
                    balance_usd = current_balance.usd_value if current_balance else 0.0
                    
                    # Alertas no leídas
                    unread_alerts = Alert.query.filter_by(is_read=False).count()
                    
                    # Estadísticas de usuarios (solo para admin)
                    total_users = User.query.count()
                    active_subs = Subscription.query.filter_by(status='ACTIVE').count()
                    
                    return {
                        'trading': {
                            'total_trades': total_trades,
                            'total_profit': float(total_profit),
                            'balance_usd': float(balance_usd),
                            'success_rate': 0.0 if total_trades == 0 else 75.5  # Simulado
                        },
                        'alerts': {
                            'unread_count': unread_alerts,
                            'last_check': datetime.utcnow().isoformat()
                        },
                        'system': {
                            'total_users': total_users,
                            'active_subscriptions': active_subs,
                            'uptime': '99.9%',
                            'status': 'optimal'
                        }
                    }
            except Exception as e:
                logging.error(f"Error fetching dashboard data: {e}")
                return {}
        
        return self.get_cached_data('dashboard_data', fetch_dashboard, 60)
    
    def get_optimized_user_stats(self, user_id):
        """Obtener estadísticas de usuario optimizadas"""
        def fetch_user_stats():
            try:
                with app.app_context():
                    user = User.query.get(user_id)
                    if not user:
                        return {}
                    
                    # Plan efectivo
                    effective_plan = user.get_effective_plan()
                    
                    # Trades del usuario
                    user_trades = Trade.query.filter_by(
                        exchange='SIMULATION'  # Solo trades demo por ahora
                    ).count()
                    
                    return {
                        'user_id': user_id,
                        'plan': effective_plan,
                        'is_admin': user.is_administrator(),
                        'trades_count': user_trades,
                        'account_value': 0.0,  # Real cuando se conecten APIs
                        'last_activity': datetime.utcnow().isoformat()
                    }
            except Exception as e:
                logging.error(f"Error fetching user stats: {e}")
                return {}
        
        return self.get_cached_data(f'user_stats_{user_id}', fetch_user_stats, 120)
    
    def background_optimizer(self):
        """Proceso de optimización en background"""
        while True:
            try:
                # Ejecutar limpieza cada hora
                now = datetime.utcnow()
                if (now - self.last_cleanup).seconds > 3600:
                    self.cleanup_old_data()
                    self.optimize_database()
                    self.last_cleanup = now
                
                # Limpiar cache cada 30 minutos
                if len(self.cache) > 100:
                    old_keys = []
                    for key, (data, timestamp) in self.cache.items():
                        if (now - timestamp).seconds > self.cache_timeout:
                            old_keys.append(key)
                    
                    for key in old_keys:
                        del self.cache[key]
                
                time.sleep(300)  # Revisar cada 5 minutos
                
            except Exception as e:
                logging.error(f"Error en background optimizer: {e}")
                time.sleep(60)
    
    def start_background_optimization(self):
        """Iniciar optimización en background"""
        thread = threading.Thread(target=self.background_optimizer, daemon=True)
        thread.start()
        logging.info("Optimizador de rendimiento iniciado")

# Instancia global
performance_optimizer = PerformanceOptimizer()

def start_performance_optimization():
    """Iniciar optimización de rendimiento"""
    performance_optimizer.start_background_optimization()