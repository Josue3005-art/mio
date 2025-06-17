"""
Sistema de notificaciones en tiempo real optimizado
"""
from app import app, db
from models import Alert, User, Trade, ArbitrageOpportunity
from datetime import datetime, timedelta
import json
import logging
from performance_optimizer import performance_optimizer

class NotificationSystem:
    """Sistema de notificaciones optimizado"""
    
    def __init__(self):
        self.active_notifications = {}
        self.notification_queue = []
        
    def create_smart_notification(self, title, message, notification_type, user_id=None, priority='normal'):
        """Crear notificación inteligente con prioridad"""
        try:
            with app.app_context():
                # Evitar duplicados recientes
                recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
                existing = Alert.query.filter(
                    Alert.title == title,
                    Alert.created_at > recent_cutoff,
                    Alert.user_id == user_id
                ).first()
                
                if existing:
                    return False, "Notificación duplicada reciente"
                
                # Crear notificación
                alert = Alert(
                    title=title,
                    message=message,
                    alert_type=notification_type.upper(),
                    user_id=user_id
                )
                
                db.session.add(alert)
                db.session.commit()
                
                # Agregar a cola de notificaciones activas
                notification_data = {
                    'id': alert.id,
                    'title': title,
                    'message': message,
                    'type': notification_type,
                    'priority': priority,
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': user_id
                }
                
                self.notification_queue.append(notification_data)
                
                return True, "Notificación creada exitosamente"
                
        except Exception as e:
            logging.error(f"Error creando notificación: {e}")
            return False, str(e)
    
    def get_user_notifications(self, user_id, limit=10):
        """Obtener notificaciones del usuario optimizado"""
        def fetch_notifications():
            try:
                with app.app_context():
                    notifications = Alert.query.filter_by(
                        user_id=user_id
                    ).order_by(Alert.created_at.desc()).limit(limit).all()
                    
                    return [{
                        'id': n.id,
                        'title': n.title,
                        'message': n.message,
                        'type': n.alert_type,
                        'is_read': n.is_read,
                        'created_at': n.created_at.isoformat() if n.created_at else None
                    } for n in notifications]
            except Exception as e:
                logging.error(f"Error fetching notifications: {e}")
                return []
        
        return performance_optimizer.get_cached_data(
            f'notifications_{user_id}', fetch_notifications, 30
        )
    
    def get_system_notifications(self, limit=20):
        """Obtener notificaciones del sistema"""
        def fetch_system_notifications():
            try:
                with app.app_context():
                    notifications = Alert.query.filter(
                        Alert.user_id.is_(None)
                    ).order_by(Alert.created_at.desc()).limit(limit).all()
                    
                    return [{
                        'id': n.id,
                        'title': n.title,
                        'message': n.message,
                        'type': n.alert_type,
                        'created_at': n.created_at.isoformat() if n.created_at else None
                    } for n in notifications]
            except Exception as e:
                logging.error(f"Error fetching system notifications: {e}")
                return []
        
        return performance_optimizer.get_cached_data(
            'system_notifications', fetch_system_notifications, 60
        )
    
    def notify_arbitrage_opportunity(self, symbol, spread_percentage, potential_profit):
        """Notificar oportunidad de arbitraje"""
        if spread_percentage >= 2.0:  # Solo spreads significativos
            title = f"Oportunidad de Arbitraje: {symbol}"
            message = f"Spread del {spread_percentage:.2f}% detectado. Ganancia potencial: ${potential_profit:.2f}"
            
            self.create_smart_notification(
                title, message, 'SUCCESS', priority='high'
            )
    
    def notify_system_event(self, event_type, details):
        """Notificar eventos del sistema"""
        event_messages = {
            'startup': 'Sistema de trading iniciado correctamente',
            'shutdown': 'Sistema de trading detenido',
            'error': f'Error del sistema: {details}',
            'optimization': 'Optimización de base de datos completada',
            'cleanup': f'Limpieza de datos completada: {details}'
        }
        
        message = event_messages.get(event_type, details)
        alert_type = 'ERROR' if event_type == 'error' else 'INFO'
        
        self.create_smart_notification(
            f"Sistema: {event_type.title()}", message, alert_type
        )
    
    def process_notification_queue(self):
        """Procesar cola de notificaciones"""
        processed = []
        
        for notification in self.notification_queue[:10]:  # Procesar máximo 10
            try:
                # Aquí se podría agregar envío por WebSocket, email, etc.
                processed.append(notification)
                
            except Exception as e:
                logging.error(f"Error procesando notificación: {e}")
        
        # Remover notificaciones procesadas
        self.notification_queue = self.notification_queue[len(processed):]
        
        return processed
    
    def mark_notifications_read(self, user_id, notification_ids=None):
        """Marcar notificaciones como leídas"""
        try:
            with app.app_context():
                query = Alert.query.filter_by(user_id=user_id, is_read=False)
                
                if notification_ids:
                    query = query.filter(Alert.id.in_(notification_ids))
                
                updated = query.update({'is_read': True})
                db.session.commit()
                
                # Limpiar cache
                cache_key = f'notifications_{user_id}'
                if cache_key in performance_optimizer.cache:
                    del performance_optimizer.cache[cache_key]
                
                return True, f"{updated} notificaciones marcadas como leídas"
                
        except Exception as e:
            logging.error(f"Error marking notifications read: {e}")
            return False, str(e)
    
    def get_notification_stats(self):
        """Obtener estadísticas de notificaciones"""
        def fetch_stats():
            try:
                with app.app_context():
                    total_alerts = Alert.query.count()
                    unread_alerts = Alert.query.filter_by(is_read=False).count()
                    
                    # Alertas por tipo en últimas 24h
                    last_24h = datetime.utcnow() - timedelta(hours=24)
                    recent_alerts = Alert.query.filter(
                        Alert.created_at > last_24h
                    ).all()
                    
                    alert_types = {}
                    for alert in recent_alerts:
                        alert_type = alert.alert_type
                        alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
                    
                    return {
                        'total_alerts': total_alerts,
                        'unread_alerts': unread_alerts,
                        'alerts_24h': len(recent_alerts),
                        'alert_types_24h': alert_types,
                        'queue_size': len(self.notification_queue)
                    }
            except Exception as e:
                logging.error(f"Error fetching notification stats: {e}")
                return {}
        
        return performance_optimizer.get_cached_data(
            'notification_stats', fetch_stats, 300
        )

# Instancia global
notification_system = NotificationSystem()

def send_notification(title, message, notification_type='INFO', user_id=None):
    """Función helper para enviar notificaciones"""
    return notification_system.create_smart_notification(
        title, message, notification_type, user_id
    )