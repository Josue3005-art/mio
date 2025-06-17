"""
Sistema de monitoreo avanzado con métricas en tiempo real
"""
from app import app, db
from models import Trade, Balance, Alert, User, Subscription, TradingConfig
from datetime import datetime, timedelta
from performance_optimizer import performance_optimizer
from notification_system import notification_system
import psutil
import threading
import time
import logging
from sqlalchemy import text

class AdvancedMonitoring:
    """Monitor avanzado del sistema"""
    
    def __init__(self):
        self.metrics = {
            'system': {},
            'database': {},
            'trading': {},
            'users': {}
        }
        self.alerts_triggered = set()
        self.monitoring_active = False
        
    def collect_system_metrics(self):
        """Recopilar métricas del sistema"""
        try:
            # Métricas de CPU y memoria
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            self.metrics['system'] = {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available': memory.available / (1024**3),  # GB
                'disk_usage': disk.percent,
                'disk_free': disk.free / (1024**3),  # GB
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Alertas de sistema
            if cpu_percent > 85:
                self._trigger_alert('high_cpu', f'Uso de CPU alto: {cpu_percent:.1f}%')
            
            if memory.percent > 90:
                self._trigger_alert('high_memory', f'Uso de memoria alto: {memory.percent:.1f}%')
                
        except Exception as e:
            logging.error(f"Error collecting system metrics: {e}")
    
    def collect_database_metrics(self):
        """Recopilar métricas de la base de datos"""
        try:
            with app.app_context():
                # Tamaño de tablas principales
                table_sizes = {}
                tables = ['trade', 'alert', 'users', 'subscription', 'balance']
                
                for table in tables:
                    try:
                        result = db.session.execute(text(f"""
                            SELECT COUNT(*) as count,
                                   pg_size_pretty(pg_total_relation_size('{table}')) as size
                            FROM {table}
                        """)).fetchone()
                        
                        table_sizes[table] = {
                            'count': result[0] if result else 0,
                            'size': result[1] if result else '0 bytes'
                        }
                    except:
                        table_sizes[table] = {'count': 0, 'size': '0 bytes'}
                
                # Conexiones activas
                try:
                    active_connections = db.session.execute(text("""
                        SELECT count(*) FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)).scalar() or 0
                except:
                    active_connections = 0
                
                self.metrics['database'] = {
                    'table_sizes': table_sizes,
                    'active_connections': active_connections,
                    'last_optimization': self._get_last_optimization(),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logging.error(f"Error collecting database metrics: {e}")
    
    def collect_trading_metrics(self):
        """Recopilar métricas de trading"""
        try:
            with app.app_context():
                # Estadísticas de trading en últimas 24h
                last_24h = datetime.utcnow() - timedelta(hours=24)
                
                trades_24h = Trade.query.filter(
                    Trade.executed_at > last_24h
                ).count()
                
                # Profit/Loss en últimas 24h
                profit_24h = db.session.execute(text("""
                    SELECT COALESCE(SUM(profit_loss), 0) 
                    FROM trade 
                    WHERE executed_at > %s
                """), (last_24h,)).scalar() or 0.0
                
                # Alertas generadas en últimas 24h
                alerts_24h = Alert.query.filter(
                    Alert.created_at > last_24h
                ).count()
                
                # Balance actual
                current_balance = Balance.query.first()
                balance_usd = current_balance.usd_value if current_balance else 0.0
                
                self.metrics['trading'] = {
                    'trades_24h': trades_24h,
                    'profit_24h': float(profit_24h),
                    'alerts_24h': alerts_24h,
                    'current_balance': float(balance_usd),
                    'success_rate': self._calculate_success_rate(),
                    'avg_trade_time': self._calculate_avg_trade_time(),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logging.error(f"Error collecting trading metrics: {e}")
    
    def collect_user_metrics(self):
        """Recopilar métricas de usuarios"""
        try:
            with app.app_context():
                total_users = User.query.count()
                admin_users = User.query.filter_by(is_admin=True).count()
                
                # Suscripciones activas por plan
                active_subs = Subscription.query.filter_by(status='ACTIVE').all()
                plan_distribution = {}
                for sub in active_subs:
                    plan = sub.plan_type
                    plan_distribution[plan] = plan_distribution.get(plan, 0) + 1
                
                # Ingresos mensuales estimados
                monthly_revenue = sum([
                    plan_distribution.get('BASIC', 0) * 29.99,
                    plan_distribution.get('PREMIUM', 0) * 99.99
                ])
                
                self.metrics['users'] = {
                    'total_users': total_users,
                    'admin_users': admin_users,
                    'active_subscriptions': len(active_subs),
                    'plan_distribution': plan_distribution,
                    'monthly_revenue': monthly_revenue,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logging.error(f"Error collecting user metrics: {e}")
    
    def _trigger_alert(self, alert_key, message):
        """Disparar alerta si no se ha disparado recientemente"""
        if alert_key not in self.alerts_triggered:
            notification_system.notify_system_event('error', message)
            self.alerts_triggered.add(alert_key)
            
            # Remover alerta después de 1 hora
            threading.Timer(3600, lambda: self.alerts_triggered.discard(alert_key)).start()
    
    def _get_last_optimization(self):
        """Obtener timestamp de última optimización"""
        try:
            config = TradingConfig.query.filter_by(key='LAST_DB_OPTIMIZATION').first()
            return config.value if config else 'Never'
        except:
            return 'Never'
    
    def _calculate_success_rate(self):
        """Calcular tasa de éxito de trades"""
        try:
            with app.app_context():
                total_trades = Trade.query.count()
                if total_trades == 0:
                    return 0.0
                
                successful_trades = Trade.query.filter(
                    Trade.profit_loss > 0
                ).count()
                
                return (successful_trades / total_trades) * 100
        except:
            return 0.0
    
    def _calculate_avg_trade_time(self):
        """Calcular tiempo promedio de trade (simulado)"""
        return 45.7  # segundos promedio simulado
    
    def get_comprehensive_metrics(self):
        """Obtener todas las métricas del sistema"""
        self.collect_system_metrics()
        self.collect_database_metrics()
        self.collect_trading_metrics()
        self.collect_user_metrics()
        
        return {
            'system': self.metrics['system'],
            'database': self.metrics['database'],
            'trading': self.metrics['trading'],
            'users': self.metrics['users'],
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def get_health_score(self):
        """Calcular puntuación de salud del sistema"""
        try:
            score = 100
            
            # Penalizar por uso alto de recursos
            if self.metrics['system'].get('cpu_usage', 0) > 80:
                score -= 20
            elif self.metrics['system'].get('cpu_usage', 0) > 60:
                score -= 10
                
            if self.metrics['system'].get('memory_usage', 0) > 85:
                score -= 15
            elif self.metrics['system'].get('memory_usage', 0) > 70:
                score -= 8
            
            # Bonificar por actividad de trading
            if self.metrics['trading'].get('trades_24h', 0) > 0:
                score += 5
            
            if self.metrics['trading'].get('profit_24h', 0) > 0:
                score += 10
            
            return max(0, min(100, score))
            
        except:
            return 50  # Puntuación neutral si hay error
    
    def monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.monitoring_active:
            try:
                self.get_comprehensive_metrics()
                
                # Actualizar cache cada 5 minutos
                performance_optimizer.cache['system_metrics'] = (
                    self.metrics, datetime.utcnow()
                )
                
                time.sleep(300)  # 5 minutos
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def start_monitoring(self):
        """Iniciar monitoreo en background"""
        if not self.monitoring_active:
            self.monitoring_active = True
            thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            thread.start()
            logging.info("Sistema de monitoreo avanzado iniciado")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.monitoring_active = False
        logging.info("Sistema de monitoreo detenido")

# Instancia global
advanced_monitor = AdvancedMonitoring()

def start_advanced_monitoring():
    """Iniciar monitoreo avanzado"""
    advanced_monitor.start_monitoring()
    
def get_system_health():
    """Obtener salud del sistema"""
    return advanced_monitor.get_health_score()
    
def get_live_metrics():
    """Obtener métricas en vivo"""
    return advanced_monitor.get_comprehensive_metrics()