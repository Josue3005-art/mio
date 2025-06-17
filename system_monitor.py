"""
Sistema de monitoreo robusto para detectar errores y problemas automáticamente
"""
import logging
import time
import threading
from datetime import datetime, timedelta
from app import app, db
from models import Alert, TradingConfig
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor del sistema para detectar problemas automáticamente"""
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 60  # segundos
        self.last_checks = {}
        
    def start_monitoring(self):
        """Iniciar monitoreo en background"""
        if not self.is_running:
            self.is_running = True
            monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            monitor_thread.start()
            logger.info("Sistema de monitoreo iniciado")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.is_running = False
        logger.info("Sistema de monitoreo detenido")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.is_running:
            try:
                self.check_database_health()
                self.check_memory_usage()
                self.check_api_endpoints()
                self.clean_old_data()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
                time.sleep(30)  # Pausa más corta en caso de error
    
    def check_database_health(self):
        """Verificar salud de la base de datos"""
        try:
            with app.app_context():
                # Test simple de conexión
                db.session.execute("SELECT 1")
                
                # Verificar tamaño de tablas
                result = db.session.execute("""
                    SELECT COUNT(*) as total_alerts FROM alert WHERE created_at > NOW() - INTERVAL '24 hours'
                """).fetchone()
                
                alert_count = result[0] if result else 0
                
                if alert_count > 1000:  # Más de 1000 alertas en 24h
                    self.create_system_alert(
                        "Alto volumen de alertas",
                        f"Se detectaron {alert_count} alertas en las últimas 24 horas",
                        "WARNING"
                    )
                
                self.last_checks['database'] = datetime.now()
                
        except Exception as e:
            logger.error(f"Error verificando base de datos: {e}")
            self.create_system_alert(
                "Error de base de datos",
                f"Fallo en verificación de BD: {str(e)[:100]}",
                "ERROR"
            )
    
    def check_memory_usage(self):
        """Verificar uso de memoria del sistema"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if memory.percent > 85:
                self.create_system_alert(
                    "Memoria alta",
                    f"Uso de memoria: {memory.percent:.1f}%",
                    "WARNING"
                )
            
            if cpu_percent > 90:
                self.create_system_alert(
                    "CPU alta",
                    f"Uso de CPU: {cpu_percent:.1f}%",
                    "WARNING"
                )
                
            self.last_checks['memory'] = datetime.now()
            
        except ImportError:
            # psutil no disponible, usar método alternativo
            pass
        except Exception as e:
            logger.error(f"Error verificando memoria: {e}")
    
    def check_api_endpoints(self):
        """Verificar que las páginas principales respondan correctamente"""
        endpoints = [
            ('/', 'Dashboard'),
            ('/analytics', 'Analytics'),
            ('/settings', 'Settings'),
            ('/subscription', 'Plans')
        ]
        
        try:
            for endpoint, name in endpoints:
                response = requests.get(f"http://localhost:5000{endpoint}", timeout=10)
                
                if response.status_code != 200:
                    self.create_system_alert(
                        f"Endpoint {name} falla",
                        f"HTTP {response.status_code} en {endpoint}",
                        "ERROR"
                    )
                elif response.elapsed.total_seconds() > 5:
                    self.create_system_alert(
                        f"Endpoint {name} lento",
                        f"Respuesta en {response.elapsed.total_seconds():.1f}s",
                        "WARNING"
                    )
            
            self.last_checks['endpoints'] = datetime.now()
            
        except requests.RequestException as e:
            logger.error(f"Error verificando endpoints: {e}")
            self.create_system_alert(
                "Endpoints no responden",
                f"Error de conectividad: {str(e)[:100]}",
                "ERROR"
            )
    
    def clean_old_data(self):
        """Limpiar datos antiguos para evitar acumulación"""
        try:
            with app.app_context():
                # Limpiar alertas antiguas (más de 30 días)
                thirty_days_ago = datetime.now() - timedelta(days=30)
                old_alerts = Alert.query.filter(Alert.created_at < thirty_days_ago).count()
                
                if old_alerts > 0:
                    Alert.query.filter(Alert.created_at < thirty_days_ago).delete()
                    db.session.commit()
                    logger.info(f"Limpiadas {old_alerts} alertas antiguas")
                
                self.last_checks['cleanup'] = datetime.now()
                
        except Exception as e:
            logger.error(f"Error limpiando datos: {e}")
    
    def create_system_alert(self, title, message, alert_type):
        """Crear alerta del sistema"""
        try:
            with app.app_context():
                # Evitar spam - solo crear si no existe una similar reciente
                recent_alert = Alert.query.filter(
                    Alert.title == title,
                    Alert.created_at > datetime.now() - timedelta(hours=1)
                ).first()
                
                if not recent_alert:
                    alert = Alert(
                        title=title,
                        message=message,
                        alert_type=alert_type
                    )
                    db.session.add(alert)
                    db.session.commit()
                    logger.warning(f"ALERTA SISTEMA: {title} - {message}")
                
        except Exception as e:
            logger.error(f"Error creando alerta: {e}")
    
    def get_system_status(self):
        """Obtener estado actual del sistema"""
        status = {
            'monitoring_active': self.is_running,
            'last_checks': self.last_checks,
            'uptime': datetime.now().isoformat()
        }
        
        # Verificar si las verificaciones están actualizadas
        now = datetime.now()
        for check_name, last_time in self.last_checks.items():
            if (now - last_time).total_seconds() > self.check_interval * 2:
                status[f'{check_name}_stale'] = True
        
        return status

# Instancia global del monitor
system_monitor = SystemMonitor()

def start_system_monitor():
    """Función para iniciar el monitor desde otras partes del código"""
    system_monitor.start_monitoring()

def get_system_status():
    """Función para obtener estado del sistema"""
    return system_monitor.get_system_status()

if __name__ == "__main__":
    # Test del monitor
    monitor = SystemMonitor()
    monitor.start_monitoring()
    
    try:
        time.sleep(120)  # Correr por 2 minutos
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()