"""
Motor de Trading Real - Opera con APIs de exchanges reales
Solo se activa cuando el usuario configura sus API keys
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from models import Trade, Alert, Configuration, Balance
from app import db
import time
import threading

class RealTradingEngine:
    """Motor de trading que opera con dinero real usando APIs configuradas"""
    
    def __init__(self):
        self.is_running = False
        self.exchanges = {}
        self.min_spread = 0.5  # Mínimo spread para arbitraje
        self.max_trade_amount = 15.0
        self.min_trade_amount = 5.0
        self.stop_loss_percentage = 2.0
        self.max_positions = 3
        self.active_positions = []
        self.last_scan = None
        
    def load_configuration(self):
        """Cargar configuración desde base de datos"""
        try:
            # Cargar configuración de trading
            config_keys = [
                'min_trade_amount', 'max_trade_amount', 'stop_loss_percentage',
                'target_spread', 'max_positions'
            ]
            
            for key in config_keys:
                config = Configuration.query.filter_by(key=key).first()
                if config:
                    setattr(self, key, float(config.value))
            
            logging.info("Configuración de trading cargada")
            
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
    
    def load_exchange_clients(self):
        """Cargar y configurar clientes de exchanges desde base de datos"""
        try:
            import ccxt
            
            # Cargar configuración de Binance
            binance_config = Configuration.query.filter_by(key='binance_config').first()
            if binance_config:
                config_data = json.loads(binance_config.value)
                if config_data.get('enabled'):
                    self.exchanges['binance'] = ccxt.binance({
                        'apiKey': config_data['api_key'],
                        'secret': config_data['api_secret'],
                        'sandbox': False,
                        'enableRateLimit': True,
                    })
                    logging.info("Cliente Binance configurado")
            
            # Cargar configuración de KuCoin
            kucoin_config = Configuration.query.filter_by(key='kucoin_config').first()
            if kucoin_config:
                config_data = json.loads(kucoin_config.value)
                if config_data.get('enabled'):
                    self.exchanges['kucoin'] = ccxt.kucoin({
                        'apiKey': config_data['api_key'],
                        'secret': config_data['api_secret'],
                        'password': config_data['passphrase'],
                        'sandbox': False,
                        'enableRateLimit': True,
                    })
                    logging.info("Cliente KuCoin configurado")
            
            if not self.exchanges:
                logging.warning("No hay exchanges configurados para trading real")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error configurando exchanges: {e}")
            return False
    
    def is_trading_mode_real(self):
        """Verificar si está en modo de trading real"""
        try:
            config = Configuration.query.filter_by(key='trading_mode').first()
            return config and config.value == 'real'
        except:
            return False
    
    def start(self):
        """Iniciar motor de trading real"""
        if self.is_running:
            return {'success': False, 'message': 'Motor ya está ejecutándose'}
        
        if not self.is_trading_mode_real():
            return {'success': False, 'message': 'Sistema en modo DEMO. Cambiar a modo REAL para operar'}
        
        if not self.load_exchange_clients():
            return {'success': False, 'message': 'Error configurando exchanges. Verificar API keys'}
        
        self.load_configuration()
        self.is_running = True
        
        # Iniciar en hilo separado
        trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
        trading_thread.start()
        
        # Crear alerta de inicio
        self.create_alert(
            'Trading Real Iniciado',
            f'Motor de trading real activado con {len(self.exchanges)} exchanges',
            'SUCCESS'
        )
        
        logging.info(f"Motor de trading real iniciado con exchanges: {list(self.exchanges.keys())}")
        return {'success': True, 'message': 'Motor de trading real iniciado exitosamente'}
    
    def stop(self):
        """Detener motor de trading"""
        self.is_running = False
        self.create_alert(
            'Trading Detenido',
            'Motor de trading real detenido por usuario',
            'INFO'
        )
        logging.info("Motor de trading real detenido")
    
    def trading_loop(self):
        """Loop principal de trading"""
        while self.is_running:
            try:
                # Verificar que sigue en modo real
                if not self.is_trading_mode_real():
                    self.stop()
                    break
                
                # Actualizar balances
                self.update_balances()
                
                # Buscar oportunidades de arbitraje
                opportunities = self.scan_arbitrage_opportunities()
                
                # Ejecutar trades si hay oportunidades
                for opportunity in opportunities:
                    if len(self.active_positions) >= self.max_positions:
                        break
                    
                    if opportunity['profit_percentage'] >= self.min_spread:
                        self.execute_arbitrage_trade(opportunity)
                
                # Gestionar posiciones abiertas
                self.manage_open_positions()
                
                # Esperar antes del siguiente ciclo
                time.sleep(2)  # Escanear cada 2 segundos
                
            except Exception as e:
                logging.error(f"Error en trading loop: {e}")
                time.sleep(5)  # Esperar más tiempo si hay error
    
    def scan_arbitrage_opportunities(self):
        """Buscar oportunidades de arbitraje entre exchanges"""
        opportunities = []
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT']
        
        try:
            for symbol in symbols:
                prices = {}
                
                # Obtener precios de todos los exchanges
                for exchange_name, client in self.exchanges.items():
                    try:
                        ticker = client.get_symbol_ticker(symbol)
                        if ticker.get('success'):
                            prices[exchange_name] = {
                                'bid': float(ticker['price']) * 0.999,  # Simular bid
                                'ask': float(ticker['price']) * 1.001   # Simular ask
                            }
                    except Exception as e:
                        logging.warning(f"Error obteniendo precio de {symbol} en {exchange_name}: {e}")
                
                # Encontrar oportunidades de arbitraje
                if len(prices) >= 2:
                    opportunity = self.find_best_arbitrage(symbol, prices)
                    if opportunity:
                        opportunities.append(opportunity)
            
            self.last_scan = datetime.now()
            return opportunities
            
        except Exception as e:
            logging.error(f"Error escaneando oportunidades: {e}")
            return []
    
    def find_best_arbitrage(self, symbol, prices):
        """Encontrar la mejor oportunidad de arbitraje para un símbolo"""
        best_opportunity = None
        max_profit = 0
        
        exchanges = list(prices.keys())
        
        for i in range(len(exchanges)):
            for j in range(len(exchanges)):
                if i != j:
                    buy_exchange = exchanges[i]
                    sell_exchange = exchanges[j]
                    
                    buy_price = prices[buy_exchange]['ask']
                    sell_price = prices[sell_exchange]['bid']
                    
                    if sell_price > buy_price:
                        profit_percentage = ((sell_price - buy_price) / buy_price) * 100
                        
                        if profit_percentage > max_profit and profit_percentage >= self.min_spread:
                            max_profit = profit_percentage
                            best_opportunity = {
                                'symbol': symbol,
                                'buy_exchange': buy_exchange,
                                'sell_exchange': sell_exchange,
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'profit_percentage': profit_percentage,
                                'estimated_profit': (sell_price - buy_price) * (self.min_trade_amount / buy_price)
                            }
        
        return best_opportunity
    
    def execute_arbitrage_trade(self, opportunity):
        """Ejecutar trade de arbitraje"""
        try:
            symbol = opportunity['symbol']
            buy_exchange = opportunity['buy_exchange']
            sell_exchange = opportunity['sell_exchange']
            trade_amount = min(self.max_trade_amount, max(self.min_trade_amount, 
                             opportunity['estimated_profit'] * 10))
            
            # Verificar balances suficientes
            if not self.has_sufficient_balance(buy_exchange, 'USDT', trade_amount):
                logging.warning(f"Balance insuficiente en {buy_exchange} para trade de {trade_amount} USDT")
                return False
            
            # Ejecutar compra
            buy_client = self.exchanges[buy_exchange]
            buy_result = buy_client.order_market_buy(symbol, trade_amount)
            
            if not buy_result.get('success'):
                logging.error(f"Error en compra: {buy_result.get('error', 'Error desconocido')}")
                return False
            
            quantity = buy_result['quantity']
            
            # Registrar trade de compra
            buy_trade = Trade(
                symbol=symbol,
                side='BUY',
                quantity=quantity,
                price=opportunity['buy_price'],
                total_value=trade_amount,
                exchange=buy_exchange,
                order_id=buy_result['order_id'],
                status='COMPLETED'
            )
            db.session.add(buy_trade)
            
            # Agregar a posiciones activas
            position = {
                'symbol': symbol,
                'quantity': quantity,
                'buy_price': opportunity['buy_price'],
                'sell_exchange': sell_exchange,
                'target_price': opportunity['sell_price'],
                'stop_loss': opportunity['buy_price'] * (1 - self.stop_loss_percentage / 100),
                'buy_trade_id': buy_trade.id,
                'opened_at': datetime.now()
            }
            self.active_positions.append(position)
            
            db.session.commit()
            
            # Crear alerta de trade ejecutado
            self.create_alert(
                'Trade Ejecutado',
                f'Arbitraje {symbol}: Compra en {buy_exchange} a ${opportunity["buy_price"]:.4f}',
                'SUCCESS'
            )
            
            logging.info(f"Trade ejecutado: {symbol} comprado en {buy_exchange}")
            return True
            
        except Exception as e:
            logging.error(f"Error ejecutando trade: {e}")
            db.session.rollback()
            return False
    
    def manage_open_positions(self):
        """Gestionar posiciones abiertas"""
        for position in self.active_positions[:]:  # Copiar lista para poder modificar
            try:
                symbol = position['symbol']
                sell_exchange = position['sell_exchange']
                
                # Obtener precio actual
                sell_client = self.exchanges[sell_exchange]
                ticker = sell_client.get_symbol_ticker(symbol)
                
                if ticker.get('success'):
                    current_price = float(ticker['price'])
                    
                    # Verificar stop loss
                    if current_price <= position['stop_loss']:
                        self.close_position(position, current_price, 'STOP_LOSS')
                        continue
                    
                    # Verificar si es rentable vender
                    if current_price >= position['target_price']:
                        self.close_position(position, current_price, 'PROFIT')
                        continue
                    
                    # Verificar timeout (cerrar después de 5 minutos)
                    if datetime.now() - position['opened_at'] > timedelta(minutes=5):
                        self.close_position(position, current_price, 'TIMEOUT')
                        continue
                        
            except Exception as e:
                logging.error(f"Error gestionando posición: {e}")
    
    def close_position(self, position, current_price, reason):
        """Cerrar una posición vendiendo"""
        try:
            symbol = position['symbol']
            quantity = position['quantity']
            sell_exchange = position['sell_exchange']
            
            sell_client = self.exchanges[sell_exchange]
            sell_result = sell_client.order_market_sell(symbol, quantity)
            
            if sell_result.get('success'):
                total_received = sell_result['total_value']
                original_cost = position['quantity'] * position['buy_price']
                profit = total_received - original_cost
                profit_percentage = (profit / original_cost) * 100
                
                # Registrar trade de venta
                sell_trade = Trade(
                    symbol=symbol,
                    side='SELL',
                    quantity=quantity,
                    price=current_price,
                    total_value=total_received,
                    exchange=sell_exchange,
                    order_id=sell_result['order_id'],
                    status='COMPLETED'
                )
                db.session.add(sell_trade)
                db.session.commit()
                
                # Remover de posiciones activas
                self.active_positions.remove(position)
                
                # Crear alerta
                alert_type = 'SUCCESS' if profit > 0 else 'WARNING'
                self.create_alert(
                    f'Posición Cerrada - {reason}',
                    f'{symbol}: Profit ${profit:.2f} ({profit_percentage:.2f}%)',
                    alert_type
                )
                
                logging.info(f"Posición cerrada: {symbol}, Profit: ${profit:.2f}")
                
        except Exception as e:
            logging.error(f"Error cerrando posición: {e}")
    
    def has_sufficient_balance(self, exchange, asset, amount):
        """Verificar si hay balance suficiente en un exchange"""
        try:
            client = self.exchanges[exchange]
            account = client.get_account()
            
            if account.get('success'):
                balances = account.get('balances', [])
                for balance in balances:
                    if balance.get('asset') == asset:
                        free_balance = float(balance.get('free', 0))
                        return free_balance >= amount
            
            return False
            
        except Exception as e:
            logging.error(f"Error verificando balance: {e}")
            return False
    
    def update_balances(self):
        """Actualizar balances de todos los exchanges"""
        try:
            for exchange_name, client in self.exchanges.items():
                account = client.get_account()
                if account.get('success'):
                    balances = account.get('balances', [])
                    
                    for balance_data in balances:
                        asset = balance_data.get('asset')
                        free = float(balance_data.get('free', 0))
                        locked = float(balance_data.get('locked', 0))
                        
                        if free > 0 or locked > 0:  # Solo guardar balances no cero
                            balance = Balance.query.filter_by(
                                exchange=exchange_name,
                                asset=asset
                            ).first()
                            
                            if balance:
                                balance.free_balance = free
                                balance.locked_balance = locked
                                balance.total_balance = free + locked
                                balance.usd_value = free + locked
                                balance.updated_at = datetime.now()
                            else:
                                balance = Balance(
                                    exchange=exchange_name,
                                    asset=asset,
                                    free_balance=free,
                                    locked_balance=locked,
                                    total_balance=free + locked,
                                    usd_value=free + locked
                                )
                                db.session.add(balance)
            
            db.session.commit()
            
        except Exception as e:
            logging.error(f"Error actualizando balances: {e}")
    
    def create_alert(self, title, message, alert_type):
        """Crear alerta en base de datos"""
        try:
            alert = Alert(
                title=title,
                message=message,
                alert_type=alert_type
            )
            db.session.add(alert)
            db.session.commit()
        except Exception as e:
            logging.error(f"Error creando alerta: {e}")
    
    def get_status(self):
        """Obtener estado del motor de trading"""
        return {
            'is_running': self.is_running,
            'exchanges_connected': len(self.exchanges),
            'active_positions': len(self.active_positions),
            'last_scan': self.last_scan.isoformat() if self.last_scan else None,
            'configuration': {
                'min_trade_amount': self.min_trade_amount,
                'max_trade_amount': self.max_trade_amount,
                'min_spread': self.min_spread,
                'max_positions': self.max_positions
            }
        }

# Instancia global del motor
real_trading_engine = RealTradingEngine()

def start_real_trading():
    """Iniciar motor de trading real"""
    return real_trading_engine.start()

def stop_real_trading():
    """Detener motor de trading real"""
    real_trading_engine.stop()

def get_trading_status():
    """Obtener estado del trading"""
    return real_trading_engine.get_status()