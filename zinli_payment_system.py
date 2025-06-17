"""
Sistema de Pagos con Zinli para Venezuela y Latinoamérica
Integración para procesar suscripciones y comisiones
"""
import requests
import json
import logging
from datetime import datetime, timedelta
from models import User, Subscription, Commission, Configuration
from app import db

class ZinliPaymentProcessor:
    """Procesador de pagos Zinli para el sistema SaaS"""
    
    def __init__(self):
        self.base_url = "https://api.zinli.com/v1"  # URL de ejemplo
        self.webhook_secret = None
        self.merchant_id = None
        self.api_key = None
        self.load_configuration()
    
    def load_configuration(self):
        """Cargar configuración de Zinli desde base de datos"""
        try:
            config = Configuration.query.filter_by(key='zinli_config').first()
            if config:
                zinli_data = json.loads(config.value)
                self.api_key = zinli_data.get('api_key')
                self.merchant_id = zinli_data.get('merchant_id')
                self.webhook_secret = zinli_data.get('webhook_secret')
                logging.info("Configuración de Zinli cargada")
        except Exception as e:
            logging.error(f"Error cargando configuración Zinli: {e}")
    
    def configure_zinli(self, api_key, merchant_id, webhook_secret):
        """Configurar credenciales de Zinli"""
        try:
            config_data = {
                'api_key': api_key,
                'merchant_id': merchant_id,
                'webhook_secret': webhook_secret,
                'enabled': True,
                'configured_at': datetime.now().isoformat()
            }
            
            config = Configuration.query.filter_by(key='zinli_config').first()
            if config:
                config.value = json.dumps(config_data)
                config.updated_at = datetime.now()
            else:
                config = Configuration(
                    key='zinli_config',
                    value=json.dumps(config_data)
                )
                db.session.add(config)
            
            db.session.commit()
            
            self.api_key = api_key
            self.merchant_id = merchant_id
            self.webhook_secret = webhook_secret
            
            return {'success': True, 'message': 'Configuración de Zinli guardada exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error configurando Zinli: {e}")
            return {'success': False, 'error': f'Error guardando configuración: {str(e)}'}
    
    def create_payment_link(self, user_id, plan_type, amount_usd):
        """Crear enlace de pago para suscripción"""
        try:
            if not self.api_key or not self.merchant_id:
                return {'success': False, 'error': 'Zinli no configurado'}
            
            # Convertir USD a VES (tasa ejemplo, en producción usar API de tasa)
            amount_ves = amount_usd * 36.5  # Tasa de ejemplo
            
            payment_data = {
                'merchant_id': self.merchant_id,
                'amount': amount_ves,
                'currency': 'VES',
                'description': f'Suscripción {plan_type} - CryptoBot Trading',
                'reference': f'SUB_{user_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'callback_url': f'https://tu-dominio.replit.app/webhook/zinli',
                'success_url': f'https://tu-dominio.replit.app/payment/success',
                'cancel_url': f'https://tu-dominio.replit.app/payment/cancel',
                'metadata': {
                    'user_id': user_id,
                    'plan_type': plan_type,
                    'amount_usd': amount_usd
                }
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # En desarrollo, simular respuesta exitosa
            if self.api_key == 'demo_key':
                return {
                    'success': True,
                    'payment_url': f'https://zinli.com/pay/demo_{payment_data["reference"]}',
                    'payment_id': f'zinli_{payment_data["reference"]}',
                    'amount_ves': amount_ves,
                    'reference': payment_data['reference']
                }
            
            # Llamada real a API de Zinli
            response = requests.post(
                f'{self.base_url}/payments',
                headers=headers,
                json=payment_data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'payment_url': result.get('payment_url'),
                    'payment_id': result.get('payment_id'),
                    'amount_ves': amount_ves,
                    'reference': payment_data['reference']
                }
            else:
                return {
                    'success': False,
                    'error': f'Error creando pago: {response.status_code}'
                }
                
        except Exception as e:
            logging.error(f"Error creando enlace de pago: {e}")
            return {'success': False, 'error': f'Error procesando pago: {str(e)}'}
    
    def process_webhook(self, webhook_data):
        """Procesar webhook de confirmación de pago"""
        try:
            # Verificar firma del webhook (en producción)
            if not self.verify_webhook_signature(webhook_data):
                return {'success': False, 'error': 'Firma inválida'}
            
            payment_status = webhook_data.get('status')
            reference = webhook_data.get('reference')
            metadata = webhook_data.get('metadata', {})
            
            if payment_status == 'completed':
                user_id = metadata.get('user_id')
                plan_type = metadata.get('plan_type')
                amount_usd = metadata.get('amount_usd')
                
                # Crear o actualizar suscripción
                result = self.activate_subscription(user_id, plan_type, amount_usd)
                
                # Procesar comisiones de referidos
                self.process_referral_commission(user_id, amount_usd)
                
                return result
            
            return {'success': True, 'message': 'Webhook procesado'}
            
        except Exception as e:
            logging.error(f"Error procesando webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_webhook_signature(self, webhook_data):
        """Verificar firma del webhook (implementar según Zinli)"""
        # En desarrollo, siempre retornar True
        return True
    
    def activate_subscription(self, user_id, plan_type, amount_usd):
        """Activar suscripción del usuario"""
        try:
            # Calcular fecha de expiración
            if plan_type == 'BASIC':
                duration_days = 30
            elif plan_type == 'PREMIUM':
                duration_days = 30
            elif plan_type == 'ENTERPRISE':
                duration_days = 30
            else:
                duration_days = 30
            
            expiry_date = datetime.now() + timedelta(days=duration_days)
            
            # Buscar suscripción existente
            subscription = Subscription.query.filter_by(
                user_id=user_id,
                status='ACTIVE'
            ).first()
            
            if subscription:
                # Extender suscripción existente
                subscription.expiry_date = expiry_date
                subscription.updated_at = datetime.now()
            else:
                # Crear nueva suscripción
                subscription = Subscription(
                    user_id=user_id,
                    plan_type=plan_type,
                    status='ACTIVE',
                    start_date=datetime.now(),
                    expiry_date=expiry_date,
                    amount_paid=amount_usd,
                    payment_method='ZINLI'
                )
                db.session.add(subscription)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Suscripción {plan_type} activada hasta {expiry_date.strftime("%Y-%m-%d")}'
            }
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error activando suscripción: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_referral_commission(self, user_id, amount_usd):
        """Procesar comisión de referido"""
        try:
            user = User.query.get(user_id)
            if not user:
                return
            
            # Buscar si el usuario fue referido
            referral = db.session.query(Commission).filter_by(
                referred_id=user_id,
                commission_type='SIGNUP'
            ).first()
            
            if referral:
                # Calcular comisión (10% del pago)
                commission_amount = amount_usd * 0.10
                
                # Crear nueva comisión mensual
                commission = Commission(
                    referrer_id=referral.referrer_id,
                    referred_id=user_id,
                    referral_code_id=referral.referral_code_id,
                    commission_amount=commission_amount,
                    commission_type='MONTHLY',
                    status='PENDING'
                )
                db.session.add(commission)
                
                # Actualizar total en código de referido
                referral_code = ReferralCode.query.get(referral.referral_code_id)
                if referral_code:
                    referral_code.total_commission += commission_amount
                
                db.session.commit()
                logging.info(f"Comisión de ${commission_amount} generada para referrer {referral.referrer_id}")
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error procesando comisión: {e}")
    
    def get_payment_plans(self):
        """Obtener planes de pago disponibles"""
        return {
            'BASIC': {
                'name': 'Plan Básico',
                'price_usd': 29.99,
                'features': [
                    'Trading automatizado',
                    'Hasta 3 exchanges',
                    'Soporte básico',
                    'Alertas por email'
                ],
                'popular': False
            },
            'PREMIUM': {
                'name': 'Plan Premium',
                'price_usd': 59.99,
                'features': [
                    'Todo del Plan Básico',
                    'Exchanges ilimitados',
                    'Estrategias avanzadas',
                    'Soporte prioritario',
                    'Alertas por Telegram',
                    'Análisis detallados'
                ],
                'popular': True
            },
            'ENTERPRISE': {
                'name': 'Plan Empresarial',
                'price_usd': 199.99,
                'features': [
                    'Todo del Plan Premium',
                    'API personalizada',
                    'Soporte 24/7',
                    'Manager dedicado',
                    'Configuración personalizada',
                    'Reportes avanzados'
                ],
                'popular': False
            }
        }
    
    def cancel_subscription(self, user_id):
        """Cancelar suscripción"""
        try:
            subscription = Subscription.query.filter_by(
                user_id=user_id,
                status='ACTIVE'
            ).first()
            
            if subscription:
                subscription.status = 'CANCELLED'
                subscription.updated_at = datetime.now()
                db.session.commit()
                
                return {'success': True, 'message': 'Suscripción cancelada'}
            else:
                return {'success': False, 'error': 'No hay suscripción activa'}
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error cancelando suscripción: {e}")
            return {'success': False, 'error': str(e)}

# Instancia global
zinli_processor = ZinliPaymentProcessor()

def get_payment_processor():
    """Obtener procesador de pagos"""
    return zinli_processor