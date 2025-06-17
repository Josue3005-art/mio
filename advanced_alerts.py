import requests
import json
import logging
from datetime import datetime, timedelta
from app import app, db
from models import Alert, TradingConfig, Trade
from advanced_strategies import AdvancedTradingStrategies

logger = logging.getLogger(__name__)

class AdvancedAlertSystem:
    """Sistema avanzado de alertas con Telegram y umbrales configurables"""
    
    def __init__(self):
        self.strategies = AdvancedTradingStrategies()
        self.telegram_bot_token = None
        self.telegram_chat_id = None
        self.load_telegram_config()
        
    def load_telegram_config(self):
        """Cargar configuración de Telegram desde base de datos"""
        try:
            with app.app_context():
                bot_token = TradingConfig.query.filter_by(key='telegram_bot_token').first()
                chat_id = TradingConfig.query.filter_by(key='telegram_chat_id').first()
                
                self.telegram_bot_token = bot_token.value if bot_token else None
                self.telegram_chat_id = chat_id.value if chat_id else None
        except Exception as e:
            logger.error(f"Error cargando config Telegram: {e}")
    
    def setup_telegram(self, bot_token, chat_id):
        """Configurar credenciales de Telegram"""
        try:
            with app.app_context():
                # Guardar bot token
                token_config = TradingConfig.query.filter_by(key='telegram_bot_token').first()
                if token_config:
                    token_config.value = bot_token
                    token_config.updated_at = datetime.utcnow()
                else:
                    token_config = TradingConfig(
                        key='telegram_bot_token',
                        value=bot_token,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(token_config)
                
                # Guardar chat ID
                chat_config = TradingConfig.query.filter_by(key='telegram_chat_id').first()
                if chat_config:
                    chat_config.value = chat_id
                    chat_config.updated_at = datetime.utcnow()
                else:
                    chat_config = TradingConfig(
                        key='telegram_chat_id',
                        value=chat_id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(chat_config)
                
                db.session.commit()
                
                self.telegram_bot_token = bot_token
                self.telegram_chat_id = chat_id
                
                return True
        except Exception as e:
            logger.error(f"Error configurando Telegram: {e}")
            return False
    
    def send_telegram_message(self, message, parse_mode='HTML'):
        """Enviar mensaje a Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram no configurado - guardando alerta en BD")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Mensaje enviado a Telegram exitosamente")
                return True
            else:
                logger.error(f"Error enviando a Telegram: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error conectando con Telegram: {e}")
            return False
    
    def get_alert_threshold(self, alert_type, default_value):
        """Obtener umbral de alerta desde configuración"""
        try:
            with app.app_context():
                config = TradingConfig.query.filter_by(key=f'alert_threshold_{alert_type}').first()
                return float(config.value) if config else default_value
        except Exception:
            return default_value
    
    def check_arbitrage_alerts(self):
        """Verificar alertas de arbitraje"""
        threshold = self.get_alert_threshold('arbitrage', 0.5)  # 0.5% por defecto
        
        try:
            # Ejecutar escaneo de arbitraje
            opportunities = self.strategies.ccxt.scan_arbitrage_opportunities()
            
            if opportunities:
                for opp in opportunities:
                    if opp.get('spread_percentage', 0) >= threshold:
                        message = f"""
🚨 <b>ARBITRAJE DETECTADO</b>
📈 Símbolo: <code>{opp.get('symbol', 'N/A')}</code>
💰 Spread: <b>{opp.get('spread_percentage', 0):.3f}%</b>
🔄 Comprar: {opp.get('buy_exchange', 'N/A')} - ${opp.get('buy_price', 0):.4f}
🔄 Vender: {opp.get('sell_exchange', 'N/A')} - ${opp.get('sell_price', 0):.4f}
💵 Ganancia estimada: ${opp.get('potential_profit', 0):.4f}

⏰ {datetime.now().strftime('%H:%M:%S')}
                        """
                        
                        self.send_telegram_message(message)
                        
                        # Guardar en BD
                        self.create_database_alert(
                            f"Arbitraje {opp.get('symbol', 'N/A')}",
                            f"Spread {opp.get('spread_percentage', 0):.3f}% detectado",
                            "SUCCESS"
                        )
        except Exception as e:
            logger.error(f"Error verificando alertas arbitraje: {e}")
    
    def check_pump_dump_alerts(self):
        """Verificar alertas de pump/dump"""
        pump_threshold = self.get_alert_threshold('pump', 3.0)  # 3% por defecto
        dump_threshold = self.get_alert_threshold('dump', -2.0)  # -2% por defecto
        
        try:
            alerts = self.strategies.pump_dump_detector()
            
            for alert in alerts:
                price_change = alert.get('price_change', 0)
                
                if (alert['type'] == 'PUMP' and price_change >= pump_threshold) or \
                   (alert['type'] == 'DUMP' and price_change <= dump_threshold):
                    
                    emoji = "🚀" if alert['type'] == 'PUMP' else "💥"
                    
                    message = f"""
{emoji} <b>{alert['type']} DETECTADO</b>
📈 Símbolo: <code>{alert.get('symbol', 'N/A')}</code>
📊 Cambio: <b>{price_change:.2f}%</b>
🎯 Confianza: {alert.get('confidence', 0):.1f}/2.0
📈 Volatilidad: {alert.get('volatility', 0):.2f}%
📦 Volumen promedio: {alert.get('avg_volume', 0):,.0f}

⚠️ <i>Revisar antes de operar</i>
⏰ {datetime.now().strftime('%H:%M:%S')}
                    """
                    
                    self.send_telegram_message(message)
                    
                    # Guardar en BD
                    self.create_database_alert(
                        f"{alert['type']} {alert.get('symbol', 'N/A')}",
                        f"{price_change:.2f}% movement detected",
                        "WARNING"
                    )
        except Exception as e:
            logger.error(f"Error verificando alertas pump/dump: {e}")
    
    def check_volume_alerts(self):
        """Verificar alertas de volumen"""
        volume_threshold = self.get_alert_threshold('volume', 150.0)  # 150% por defecto
        
        try:
            for symbol in ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']:
                volumes = []
                
                for exchange in ['gateio', 'mexc', 'okx', 'bitget']:
                    try:
                        ticker = self.strategies.ccxt.get_ticker(exchange, symbol)
                        if ticker and 'baseVolume' in ticker:
                            volumes.append(float(ticker['baseVolume']))
                    except Exception:
                        continue
                
                if len(volumes) >= 2:
                    avg_volume = sum(volumes) / len(volumes)
                    max_volume = max(volumes)
                    
                    if max_volume > avg_volume * (volume_threshold / 100):
                        message = f"""
📊 <b>SPIKE DE VOLUMEN</b>
📈 Símbolo: <code>{symbol}</code>
📦 Volumen máximo: {max_volume:,.0f}
📊 Volumen promedio: {avg_volume:,.0f}
🔥 Incremento: {(max_volume/avg_volume-1)*100:.1f}%

💡 <i>Posible actividad inusual</i>
⏰ {datetime.now().strftime('%H:%M:%S')}
                        """
                        
                        self.send_telegram_message(message)
                        
                        # Guardar en BD
                        self.create_database_alert(
                            f"Volume Spike {symbol}",
                            f"{(max_volume/avg_volume-1)*100:.1f}% volume increase",
                            "INFO"
                        )
        except Exception as e:
            logger.error(f"Error verificando alertas volumen: {e}")
    
    def send_daily_summary(self):
        """Enviar resumen diario"""
        try:
            with app.app_context():
                today = datetime.now().date()
                today_start = datetime.combine(today, datetime.min.time())
                
                # Estadísticas del día
                today_trades = Trade.query.filter(Trade.executed_at >= today_start).all()
                today_alerts = Alert.query.filter(Alert.created_at >= today_start).count()
                
                total_trades = len(today_trades)
                total_profit = sum(trade.profit_loss for trade in today_trades if trade.profit_loss) or 0.0
                successful_trades = len([t for t in today_trades if t.profit_loss and t.profit_loss > 0])
                win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
                
                message = f"""
📊 <b>RESUMEN DIARIO</b>
📅 {today.strftime('%d/%m/%Y')}

💼 <b>Trading:</b>
• Operaciones: {total_trades}
• Exitosas: {successful_trades}
• Tasa éxito: {win_rate:.1f}%
• P/L total: ${total_profit:.4f}

🚨 <b>Alertas:</b>
• Total hoy: {today_alerts}

🎯 <b>Sistema:</b>
• Estado: ACTIVO
• Modo: SIMULACIÓN
• Capital: $30.00

⏰ {datetime.now().strftime('%H:%M:%S')}
                """
                
                self.send_telegram_message(message)
                
        except Exception as e:
            logger.error(f"Error enviando resumen diario: {e}")
    
    def send_startup_notification(self):
        """Enviar notificación de inicio del sistema"""
        message = f"""
🤖 <b>CRYPTO ARBITRAGE BOT</b>
✅ Sistema iniciado correctamente

🔧 <b>Configuración:</b>
• Exchanges: Gate.io, MEXC, OKX, Bitget
• Símbolos: BTC, ETH, ADA, DOGE, XRP
• Modo: SIMULACIÓN
• Capital: $30.00

📋 <b>Estrategias activas:</b>
• Arbitraje entre exchanges
• Grid Trading
• Scalping
• Detección Pump/Dump
• Análisis de momentum

🚨 Alertas configuradas y funcionando
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """
        
        self.send_telegram_message(message)
    
    def create_database_alert(self, title, message, alert_type):
        """Crear alerta en base de datos"""
        try:
            with app.app_context():
                alert = Alert(
                    title=title,
                    message=message,
                    alert_type=alert_type,
                    created_at=datetime.utcnow()
                )
                db.session.add(alert)
                db.session.commit()
        except Exception as e:
            logger.error(f"Error creando alerta en BD: {e}")
    
    def test_telegram_connection(self):
        """Probar conexión con Telegram"""
        if not self.telegram_bot_token:
            return False, "Bot token no configurado"
        
        test_message = f"""
🧪 <b>TEST DE CONEXIÓN</b>
✅ Bot configurado correctamente
⏰ {datetime.now().strftime('%H:%M:%S')}

Este es un mensaje de prueba del sistema de alertas.
        """
        
        success = self.send_telegram_message(test_message)
        
        if success:
            return True, "Conexión exitosa con Telegram"
        else:
            return False, "Error conectando con Telegram"
    
    def run_all_alert_checks(self):
        """Ejecutar todas las verificaciones de alertas"""
        logger.info("Ejecutando verificaciones de alertas...")
        
        try:
            # Verificar diferentes tipos de alertas
            self.check_arbitrage_alerts()
            self.check_pump_dump_alerts()
            self.check_volume_alerts()
            
            logger.info("Verificaciones de alertas completadas")
            return True
            
        except Exception as e:
            logger.error(f"Error en verificaciones de alertas: {e}")
            return False

if __name__ == '__main__':
    alert_system = AdvancedAlertSystem()
    
    print("=== SISTEMA DE ALERTAS AVANZADO ===")
    print("Ejecutando verificaciones...")
    
    result = alert_system.run_all_alert_checks()
    
    if result:
        print("✅ Verificaciones completadas exitosamente")
    else:
        print("❌ Error en verificaciones de alertas")