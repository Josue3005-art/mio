import uuid
import string
import random
from datetime import datetime, timedelta
from flask_login import current_user
from app import app, db
from models import User, Subscription, UserSettings, UserBalance, ReferralCode, Commission
import logging

logger = logging.getLogger(__name__)

class SaaSManager:
    """Gestor del sistema SaaS multiusuario"""
    
    PLAN_FEATURES = {
        'FREE': {
            'name': 'Plan Gratuito',
            'price': 0.0,
            'max_trades_per_day': 5,
            'exchanges_access': ['gateio'],
            'strategies': ['arbitrage'],
            'telegram_alerts': False,
            'api_access': False,
            'referral_commission': 5.0  # 5%
        },
        'BASIC': {
            'name': 'Plan Básico',
            'price': 29.99,
            'max_trades_per_day': 50,
            'exchanges_access': ['gateio', 'mexc'],
            'strategies': ['arbitrage', 'scalping'],
            'telegram_alerts': True,
            'api_access': True,
            'referral_commission': 10.0  # 10%
        },
        'PREMIUM': {
            'name': 'Plan Premium',
            'price': 99.99,
            'max_trades_per_day': -1,  # Ilimitado
            'exchanges_access': ['gateio', 'mexc', 'okx', 'bitget'],
            'strategies': ['arbitrage', 'scalping', 'grid_trading', 'pump_dump'],
            'telegram_alerts': True,
            'api_access': True,
            'referral_commission': 15.0  # 15%
        }
    }
    
    def __init__(self):
        pass
    
    def create_user_subscription(self, user_id, plan_type='FREE', referral_code=None):
        """Crear suscripción para nuevo usuario"""
        try:
            with app.app_context():
                # Verificar si ya tiene suscripción activa
                existing_sub = Subscription.query.filter_by(
                    user_id=user_id, 
                    status='ACTIVE'
                ).first()
                
                if existing_sub:
                    return existing_sub
                
                # Crear nueva suscripción
                end_date = None
                if plan_type != 'FREE':
                    end_date = datetime.utcnow() + timedelta(days=30)
                
                subscription = Subscription(
                    user_id=user_id,
                    plan_type=plan_type,
                    status='ACTIVE',
                    start_date=datetime.utcnow(),
                    end_date=end_date,
                    monthly_fee=self.PLAN_FEATURES[plan_type]['price']
                )
                
                db.session.add(subscription)
                
                # Crear configuración de usuario
                user_settings = UserSettings(
                    user_id=user_id,
                    trading_enabled=False,
                    max_trade_amount=10.0 if plan_type == 'FREE' else 50.0,
                    risk_level='LOW',
                    preferred_exchanges=','.join(self.PLAN_FEATURES[plan_type]['exchanges_access'][:2]),
                    preferred_symbols='BTC/USDT,ETH/USDT'
                )
                
                db.session.add(user_settings)
                
                # Balance inicial simulado
                initial_balance = UserBalance(
                    user_id=user_id,
                    asset='USDT',
                    free_balance=30.0,
                    locked_balance=0.0,
                    total_balance=30.0,
                    usd_value=30.0,
                    exchange='SIMULATION'
                )
                
                db.session.add(initial_balance)
                
                # Procesar referido si existe
                if referral_code:
                    self.process_referral(user_id, referral_code)
                
                db.session.commit()
                
                logger.info(f"Suscripción {plan_type} creada para usuario {user_id}")
                return subscription
                
        except Exception as e:
            logger.error(f"Error creando suscripción: {e}")
            db.session.rollback()
            return None
    
    def upgrade_subscription(self, user_id, new_plan_type):
        """Actualizar plan de suscripción"""
        try:
            with app.app_context():
                # Buscar suscripción actual
                current_sub = Subscription.query.filter_by(
                    user_id=user_id,
                    status='ACTIVE'
                ).first()
                
                if not current_sub:
                    return False, "No se encontró suscripción activa"
                
                # Verificar si es una mejora válida
                plan_hierarchy = ['FREE', 'BASIC', 'PREMIUM']
                current_level = plan_hierarchy.index(current_sub.plan_type)
                new_level = plan_hierarchy.index(new_plan_type)
                
                if new_level <= current_level:
                    return False, "Solo se pueden hacer upgrades"
                
                # Actualizar suscripción
                current_sub.plan_type = new_plan_type
                current_sub.monthly_fee = self.PLAN_FEATURES[new_plan_type]['price']
                current_sub.updated_at = datetime.utcnow()
                
                if new_plan_type != 'FREE':
                    current_sub.end_date = datetime.utcnow() + timedelta(days=30)
                
                # Actualizar configuración de usuario
                user_settings = UserSettings.query.filter_by(user_id=user_id).first()
                if user_settings:
                    user_settings.max_trade_amount = 50.0 if new_plan_type == 'BASIC' else 100.0
                    user_settings.preferred_exchanges = ','.join(
                        self.PLAN_FEATURES[new_plan_type]['exchanges_access']
                    )
                    user_settings.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Usuario {user_id} actualizado a plan {new_plan_type}")
                return True, f"Plan actualizado a {self.PLAN_FEATURES[new_plan_type]['name']}"
                
        except Exception as e:
            logger.error(f"Error actualizando suscripción: {e}")
            db.session.rollback()
            return False, "Error interno del servidor"
    
    def cancel_subscription(self, user_id):
        """Cancelar suscripción (downgrade a FREE)"""
        try:
            with app.app_context():
                subscription = Subscription.query.filter_by(
                    user_id=user_id,
                    status='ACTIVE'
                ).first()
                
                if not subscription:
                    return False, "No se encontró suscripción activa"
                
                # Cambiar a plan gratuito
                subscription.plan_type = 'FREE'
                subscription.monthly_fee = 0.0
                subscription.end_date = None
                subscription.updated_at = datetime.utcnow()
                
                # Actualizar configuración
                user_settings = UserSettings.query.filter_by(user_id=user_id).first()
                if user_settings:
                    user_settings.trading_enabled = False
                    user_settings.max_trade_amount = 10.0
                    user_settings.preferred_exchanges = 'gateio'
                    user_settings.telegram_enabled = False
                    user_settings.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Suscripción cancelada para usuario {user_id}")
                return True, "Suscripción cancelada, cuenta downgraded a plan gratuito"
                
        except Exception as e:
            logger.error(f"Error cancelando suscripción: {e}")
            db.session.rollback()
            return False, "Error cancelando suscripción"
    
    def generate_referral_code(self, user_id):
        """Generar código de referido único"""
        try:
            with app.app_context():
                # Verificar si ya tiene código
                existing_code = ReferralCode.query.filter_by(
                    referrer_id=user_id,
                    is_active=True
                ).first()
                
                if existing_code:
                    return existing_code.code
                
                # Generar código único
                while True:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    
                    # Verificar que no exista
                    if not ReferralCode.query.filter_by(code=code).first():
                        break
                
                # Crear código de referido
                referral_code = ReferralCode(
                    referrer_id=user_id,
                    code=code,
                    uses_count=0,
                    total_commission=0.0,
                    is_active=True
                )
                
                db.session.add(referral_code)
                db.session.commit()
                
                logger.info(f"Código de referido {code} generado para usuario {user_id}")
                return code
                
        except Exception as e:
            logger.error(f"Error generando código de referido: {e}")
            db.session.rollback()
            return None
    
    def process_referral(self, new_user_id, referral_code):
        """Procesar referido y calcular comisiones"""
        try:
            with app.app_context():
                # Buscar código de referido
                ref_code = ReferralCode.query.filter_by(
                    code=referral_code,
                    is_active=True
                ).first()
                
                if not ref_code:
                    return False, "Código de referido inválido"
                
                # Verificar que no se auto-refiera
                if ref_code.referrer_id == new_user_id:
                    return False, "No puedes usar tu propio código"
                
                # Obtener plan del nuevo usuario
                new_user_sub = Subscription.query.filter_by(
                    user_id=new_user_id,
                    status='ACTIVE'
                ).first()
                
                if not new_user_sub:
                    return False, "Usuario sin suscripción activa"
                
                # Calcular comisión
                referrer_sub = Subscription.query.filter_by(
                    user_id=ref_code.referrer_id,
                    status='ACTIVE'
                ).first()
                
                if referrer_sub:
                    commission_rate = self.PLAN_FEATURES[referrer_sub.plan_type]['referral_commission'] / 100
                    commission_amount = new_user_sub.monthly_fee * commission_rate
                    
                    # Crear registro de comisión
                    commission = Commission(
                        referrer_id=ref_code.referrer_id,
                        referred_id=new_user_id,
                        referral_code_id=ref_code.id,
                        commission_amount=commission_amount,
                        commission_type='SIGNUP',
                        status='PENDING'
                    )
                    
                    db.session.add(commission)
                    
                    # Actualizar estadísticas del código
                    ref_code.uses_count += 1
                    ref_code.total_commission += commission_amount
                    
                    db.session.commit()
                    
                    logger.info(f"Comisión ${commission_amount:.2f} generada para usuario {ref_code.referrer_id}")
                    return True, f"Referido procesado, comisión: ${commission_amount:.2f}"
                
                return True, "Referido procesado sin comisión"
                
        except Exception as e:
            logger.error(f"Error procesando referido: {e}")
            db.session.rollback()
            return False, "Error procesando referido"
    
    def get_user_stats(self, user_id):
        """Obtener estadísticas del usuario"""
        try:
            with app.app_context():
                # Suscripción actual
                subscription = Subscription.query.filter_by(
                    user_id=user_id,
                    status='ACTIVE'
                ).first()
                
                # Configuración
                settings = UserSettings.query.filter_by(user_id=user_id).first()
                
                # Balance
                balance = UserBalance.query.filter_by(user_id=user_id).first()
                
                # Códigos de referido
                referral_codes = ReferralCode.query.filter_by(
                    referrer_id=user_id,
                    is_active=True
                ).all()
                
                # Comisiones ganadas
                total_commissions = db.session.query(
                    db.func.sum(Commission.commission_amount)
                ).filter_by(referrer_id=user_id, status='PENDING').scalar() or 0.0
                
                return {
                    'subscription': {
                        'plan_type': subscription.plan_type if subscription else 'FREE',
                        'plan_name': self.PLAN_FEATURES[subscription.plan_type if subscription else 'FREE']['name'],
                        'monthly_fee': subscription.monthly_fee if subscription else 0.0,
                        'end_date': subscription.end_date if subscription else None,
                        'features': self.PLAN_FEATURES[subscription.plan_type if subscription else 'FREE']
                    },
                    'settings': {
                        'trading_enabled': settings.trading_enabled if settings else False,
                        'max_trade_amount': settings.max_trade_amount if settings else 10.0,
                        'risk_level': settings.risk_level if settings else 'LOW',
                        'telegram_enabled': settings.telegram_enabled if settings else False
                    },
                    'balance': {
                        'total_usd': balance.usd_value if balance else 30.0,
                        'asset': balance.asset if balance else 'USDT',
                        'free_balance': balance.free_balance if balance else 30.0
                    },
                    'referrals': {
                        'codes': [code.code for code in referral_codes],
                        'total_uses': sum(code.uses_count for code in referral_codes),
                        'pending_commissions': total_commissions
                    }
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return None
    
    def check_plan_limits(self, user_id, action_type):
        """Verificar límites del plan del usuario"""
        try:
            with app.app_context():
                subscription = Subscription.query.filter_by(
                    user_id=user_id,
                    status='ACTIVE'
                ).first()
                
                if not subscription:
                    return False, "Sin suscripción activa"
                
                plan_features = self.PLAN_FEATURES[subscription.plan_type]
                
                if action_type == 'trade':
                    # Verificar límite de trades diarios
                    if plan_features['max_trades_per_day'] != -1:
                        today = datetime.now().date()
                        today_start = datetime.combine(today, datetime.min.time())
                        
                        from models import UserTrade
                        today_trades = UserTrade.query.filter(
                            UserTrade.user_id == user_id,
                            UserTrade.executed_at >= today_start
                        ).count()
                        
                        if today_trades >= plan_features['max_trades_per_day']:
                            return False, f"Límite diario de {plan_features['max_trades_per_day']} trades alcanzado"
                
                elif action_type == 'telegram':
                    if not plan_features['telegram_alerts']:
                        return False, "Alertas Telegram no disponibles en su plan"
                
                elif action_type == 'api':
                    if not plan_features['api_access']:
                        return False, "Acceso API no disponible en su plan"
                
                return True, "Acción permitida"
                
        except Exception as e:
            logger.error(f"Error verificando límites: {e}")
            return False, "Error verificando permisos"
    
    def get_all_users_stats(self):
        """Obtener estadísticas generales del SaaS"""
        try:
            with app.app_context():
                total_users = User.query.count()
                
                # Usuarios por plan
                plan_stats = {}
                for plan in ['FREE', 'BASIC', 'PREMIUM']:
                    count = Subscription.query.filter_by(plan_type=plan, status='ACTIVE').count()
                    plan_stats[plan] = count
                
                # Ingresos mensuales
                monthly_revenue = db.session.query(
                    db.func.sum(Subscription.monthly_fee)
                ).filter_by(status='ACTIVE').scalar() or 0.0
                
                # Comisiones pendientes
                pending_commissions = db.session.query(
                    db.func.sum(Commission.commission_amount)
                ).filter_by(status='PENDING').scalar() or 0.0
                
                return {
                    'total_users': total_users,
                    'plan_distribution': plan_stats,
                    'monthly_revenue': monthly_revenue,
                    'pending_commissions': pending_commissions,
                    'conversion_rate': (plan_stats['BASIC'] + plan_stats['PREMIUM']) / max(total_users, 1) * 100
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas generales: {e}")
            return None

# Instancia global del gestor SaaS
saas_manager = SaaSManager()

if __name__ == '__main__':
    print("=== CRYPTO ARBITRAGE SAAS MANAGER ===")
    
    # Mostrar características de los planes
    for plan, features in SaaSManager.PLAN_FEATURES.items():
        print(f"\n{plan} - {features['name']}:")
        print(f"  Precio: ${features['price']}/mes")
        print(f"  Trades/día: {features['max_trades_per_day'] if features['max_trades_per_day'] != -1 else 'Ilimitado'}")
        print(f"  Exchanges: {', '.join(features['exchanges_access'])}")
        print(f"  Estrategias: {', '.join(features['strategies'])}")
        print(f"  Telegram: {'Sí' if features['telegram_alerts'] else 'No'}")
        print(f"  Comisión referidos: {features['referral_commission']}%")