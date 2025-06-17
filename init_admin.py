#!/usr/bin/env python3
"""
Script de inicialización para configurar el sistema administrativo
"""
from app import app, db
from models import User, Subscription, TradingConfig
from admin_manager import setup_initial_admin
import logging

def initialize_system():
    """Inicializar el sistema con configuración básica"""
    print("🚀 Inicializando sistema de administración...")
    
    with app.app_context():
        try:
            # Crear usuario administrador demo
            demo_user_id = '1'
            user = User.query.get(demo_user_id)
            
            if not user:
                print("📝 Creando usuario administrador...")
                user = User()
                user.id = demo_user_id
                user.email = "admin@trading-bot.com"
                user.first_name = "Super"
                user.last_name = "Admin"
                user.is_admin = True
                user.role = 'SUPER_ADMIN'
                db.session.add(user)
                db.session.commit()
                print("✅ Usuario administrador creado")
            else:
                # Asegurar que sea administrador
                user.is_admin = True
                user.role = 'SUPER_ADMIN'
                db.session.commit()
                print("✅ Usuario existente actualizado como administrador")
            
            # Configurar acceso ilimitado
            success, message = setup_initial_admin(demo_user_id)
            if success:
                print(f"✅ {message}")
            else:
                print(f"⚠️ {message}")
            
            # Configuración básica del sistema
            configs = [
                ('TELEGRAM_BOT_TOKEN', ''),
                ('TELEGRAM_CHAT_ID', ''),
                ('TRADING_ENABLED', 'false'),
                ('MAX_TRADE_AMOUNT', '30.0'),
                ('RISK_LEVEL', 'LOW'),
                ('ALERT_THRESHOLD_ARBITRAGE', '2.0'),
                ('ALERT_THRESHOLD_PUMP', '15.0'),
                ('ALERT_THRESHOLD_VOLUME', '300.0'),
                ('DEMO_MODE', 'true')
            ]
            
            for key, default_value in configs:
                existing = TradingConfig.query.filter_by(key=key).first()
                if not existing:
                    config = TradingConfig(key=key, value=default_value)
                    db.session.add(config)
            
            db.session.commit()
            print("✅ Configuración básica del sistema completada")
            
            # Mostrar información del administrador
            print("\n" + "="*50)
            print("🎯 SISTEMA CONFIGURADO CORRECTAMENTE")
            print("="*50)
            print(f"👤 Usuario Administrador: {user.email}")
            print(f"🔑 ID de Usuario: {user.id}")
            print(f"👑 Rol: {user.role}")
            print(f"✨ Acceso: Completo e Ilimitado")
            print("\n📋 Funciones disponibles:")
            print("   • Gestionar usuarios y licencias")
            print("   • Crear códigos de referido")
            print("   • Acceso a todas las funciones premium")
            print("   • Panel de administración completo")
            print("\n🌐 URLs importantes:")
            print("   • Dashboard: http://localhost:5000/")
            print("   • Panel Admin: http://localhost:5000/admin")
            print("   • Planes: http://localhost:5000/subscription")
            print("="*50)
            
            return True
            
        except Exception as e:
            print(f"❌ Error durante la inicialización: {str(e)}")
            logging.error(f"Init error: {e}")
            return False

if __name__ == "__main__":
    print("🔧 Iniciando configuración del sistema...")
    success = initialize_system()
    if success:
        print("🎉 ¡Sistema listo para usar!")
    else:
        print("💥 Error en la configuración del sistema")