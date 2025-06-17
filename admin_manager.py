"""
Sistema de administración para gestionar usuarios, planes y licencias
"""
from app import app, db
from models import User, Subscription, Commission, ReferralCode
from datetime import datetime, timedelta
import secrets
import string

class AdminManager:
    """Gestor de funciones administrativas"""
    
    def __init__(self):
        pass
    
    def create_admin_user(self, user_id, email=None):
        """Crear o convertir usuario en administrador"""
        try:
            with app.app_context():
                user = User.query.get(user_id)
                if user:
                    user.is_admin = True
                    user.role = 'SUPER_ADMIN'
                    db.session.commit()
                    return True, f"Usuario {user_id} convertido en administrador"
                else:
                    return False, "Usuario no encontrado"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def grant_unlimited_access(self, user_id):
        """Otorgar acceso ilimitado a un usuario"""
        try:
            with app.app_context():
                # Crear suscripción ADMIN permanente
                existing_sub = Subscription.query.filter_by(
                    user_id=user_id,
                    plan_type='ADMIN'
                ).first()
                
                if not existing_sub:
                    admin_subscription = Subscription(
                        user_id=user_id,
                        plan_type='ADMIN',
                        status='ACTIVE',
                        start_date=datetime.utcnow(),
                        end_date=None,  # Sin fecha de expiración
                        monthly_fee=0.0
                    )
                    db.session.add(admin_subscription)
                    db.session.commit()
                    return True, "Acceso administrativo otorgado"
                else:
                    return True, "Usuario ya tiene acceso administrativo"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def create_license_for_user(self, user_id, plan_type='PREMIUM', duration_months=1):
        """Crear licencia para un usuario específico"""
        try:
            with app.app_context():
                # Cancelar suscripción actual si existe
                current_sub = Subscription.query.filter_by(
                    user_id=user_id,
                    status='ACTIVE'
                ).first()
                
                if current_sub:
                    current_sub.status = 'CANCELLED'
                
                # Crear nueva suscripción
                end_date = datetime.utcnow() + timedelta(days=30 * duration_months)
                monthly_fees = {'FREE': 0.0, 'BASIC': 29.99, 'PREMIUM': 99.99}
                
                new_subscription = Subscription(
                    user_id=user_id,
                    plan_type=plan_type,
                    status='ACTIVE',
                    start_date=datetime.utcnow(),
                    end_date=end_date,
                    monthly_fee=monthly_fees.get(plan_type, 0.0)
                )
                
                db.session.add(new_subscription)
                db.session.commit()
                
                return True, f"Licencia {plan_type} creada por {duration_months} meses"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def generate_referral_code(self, user_id, custom_code=None):
        """Generar código de referido para un usuario"""
        try:
            with app.app_context():
                if custom_code:
                    code = custom_code.upper()
                else:
                    # Generar código aleatorio
                    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                
                # Verificar que el código no exista
                existing = ReferralCode.query.filter_by(code=code).first()
                if existing:
                    return False, "El código ya existe"
                
                referral_code = ReferralCode(
                    referrer_id=user_id,
                    code=code,
                    uses_count=0,
                    total_commission=0.0,
                    is_active=True
                )
                
                db.session.add(referral_code)
                db.session.commit()
                
                return True, f"Código de referido creado: {code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def list_all_users(self):
        """Listar todos los usuarios del sistema"""
        try:
            with app.app_context():
                users = User.query.all()
                user_list = []
                
                for user in users:
                    subscription = Subscription.query.filter_by(
                        user_id=user.id,
                        status='ACTIVE'
                    ).first()
                    
                    user_info = {
                        'id': user.id,
                        'email': user.email,
                        'name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                        'is_admin': user.is_admin,
                        'role': user.role,
                        'plan': subscription.plan_type if subscription else 'FREE',
                        'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A'
                    }
                    user_list.append(user_info)
                
                return True, user_list
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def change_user_plan(self, user_id, new_plan, admin_override=True):
        """Cambiar plan de usuario (solo administradores)"""
        try:
            with app.app_context():
                if new_plan not in ['FREE', 'BASIC', 'PREMIUM']:
                    return False, "Plan no válido"
                
                # Cancelar suscripción actual
                current_sub = Subscription.query.filter_by(
                    user_id=user_id,
                    status='ACTIVE'
                ).first()
                
                if current_sub:
                    current_sub.status = 'CANCELLED'
                
                # Crear nueva suscripción solo si no es FREE
                if new_plan != 'FREE':
                    monthly_fees = {'BASIC': 29.99, 'PREMIUM': 99.99}
                    end_date = datetime.utcnow() + timedelta(days=30) if admin_override else None
                    
                    new_subscription = Subscription(
                        user_id=user_id,
                        plan_type=new_plan,
                        status='ACTIVE',
                        start_date=datetime.utcnow(),
                        end_date=end_date,
                        monthly_fee=monthly_fees.get(new_plan, 0.0)
                    )
                    
                    db.session.add(new_subscription)
                
                db.session.commit()
                return True, f"Plan cambiado a {new_plan}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_system_stats(self):
        """Obtener estadísticas del sistema"""
        try:
            with app.app_context():
                total_users = User.query.count()
                admin_users = User.query.filter_by(is_admin=True).count()
                
                active_subs = Subscription.query.filter_by(status='ACTIVE').count()
                free_users = total_users - active_subs
                
                basic_subs = Subscription.query.filter_by(
                    plan_type='BASIC', status='ACTIVE'
                ).count()
                
                premium_subs = Subscription.query.filter_by(
                    plan_type='PREMIUM', status='ACTIVE'
                ).count()
                
                total_codes = ReferralCode.query.count()
                active_codes = ReferralCode.query.filter_by(is_active=True).count()
                
                stats = {
                    'total_users': total_users,
                    'admin_users': admin_users,
                    'free_users': free_users,
                    'basic_subscribers': basic_subs,
                    'premium_subscribers': premium_subs,
                    'total_referral_codes': total_codes,
                    'active_referral_codes': active_codes,
                    'monthly_revenue': (basic_subs * 29.99) + (premium_subs * 99.99)
                }
                
                return True, stats
        except Exception as e:
            return False, f"Error: {str(e)}"

# Instancia global del administrador
admin_manager = AdminManager()

def setup_initial_admin(user_id):
    """Configurar el primer administrador del sistema"""
    success1, msg1 = admin_manager.create_admin_user(user_id)
    success2, msg2 = admin_manager.grant_unlimited_access(user_id)
    
    if success1 and success2:
        return True, "Administrador inicial configurado correctamente"
    else:
        return False, f"Error configurando admin: {msg1}, {msg2}"

def is_user_admin(user_id):
    """Verificar si un usuario es administrador"""
    try:
        with app.app_context():
            user = User.query.get(user_id)
            return user and user.is_administrator()
    except:
        return False