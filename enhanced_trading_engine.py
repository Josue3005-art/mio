import subprocess
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from app import db
from models import Trade, Balance, DailyStats, TradingConfig, Alert

class EnhancedTradingEngine:
    """Motor de trading mejorado con CCXT y APIs reales"""
    
    def __init__(self, telegram_bot=None):
        self.telegram_bot = telegram_bot
        self.is_running = False
        self.positions = {}
        
        # Configuración de trading
        self.min_trade_amount = 5.0
        self.target_spread = 0.003  # 0.3% mínimo
        self.stop_loss_percentage = 0.02  # 2% stop loss
        
        # Exchanges disponibles (sin sandbox para usar APIs reales)
        self.exchanges = ['binance', 'okx']
        self.target_symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT']
        
        logging.info("Enhanced Trading Engine initialized with CCXT")
    
    def run_ccxt_command(self, command, exchange, symbol=None, params=None):
        """Ejecutar comando CCXT"""
        try:
            # Obtener credenciales desde configuración
            api_key = self.get_config(f'{exchange}_api_key')
            api_secret = self.get_config(f'{exchange}_api_secret')
            
            script = f"""
const ccxt = require('ccxt');

async function execute() {{
    try {{
        const exchange = new ccxt.{exchange}({{
            apiKey: '{api_key or ""}',
            secret: '{api_secret or ""}',
            sandbox: false,
            enableRateLimit: true,
        }});
        
        let result;
        switch ('{command}') {{
            case 'fetch_ticker':
                result = await exchange.fetchTicker('{symbol or "BTC/USDT"}');
                break;
            case 'fetch_order_book':
                result = await exchange.fetchOrderBook('{symbol or "BTC/USDT"}');
                break;
            case 'fetch_balance':
                result = await exchange.fetchBalance();
                break;
            case 'create_market_buy_order':
                result = await exchange.createMarketBuyOrder('{symbol}', null, null, {params or '{}'});
                break;
            case 'create_market_sell_order':
                result = await exchange.createMarketSellOrder('{symbol}', {params or 0}, null, {{}});
                break;
            default:
                throw new Error('Unknown command: {command}');
        }}
        
        console.log(JSON.stringify(result));
    }} catch (error) {{
        console.error(JSON.stringify({{error: error.message}}));
    }}
}}

execute();
"""
            
            # Escribir y ejecutar script
            with open('/tmp/ccxt_script.js', 'w') as f:
                f.write(script)
            
            result = subprocess.run(
                ['node', '/tmp/ccxt_script.js'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logging.error(f"CCXT error: {result.stderr}")
                return None
                
        except Exception as e:
            logging.error(f"Error running CCXT command: {e}")
            return None
    
    def get_config(self, key):
        """Obtener configuración desde base de datos"""
        try:
            config = TradingConfig.query.filter_by(key=key).first()
            return config.value if config else None
        except:
            return None
    
    def start(self):
        """Iniciar el motor de trading"""
        self.is_running = True
        logging.info("Starting Enhanced Trading Engine...")
        
        while self.is_running:
            try:
                self.update_balances()
                self.scan_arbitrage_opportunities()
                self.manage_positions()
                
                time.sleep(10)  # Check cada 10 segundos
                
            except Exception as e:
                logging.error(f"Error in trading loop: {e}")
                time.sleep(30)
    
    def update_balances(self):
        """Actualizar balances desde exchanges reales"""
        try:
            total_usd_value = 0
            
            with db.session.begin():
                # Limpiar balances existentes
                Balance.query.delete()
                
                for exchange in self.exchanges:
                    balance_data = self.run_ccxt_command('fetch_balance', exchange)
                    
                    if balance_data and 'total' in balance_data:
                        for asset, amounts in balance_data['total'].items():
                            if amounts > 0:
                                # Obtener valor en USD
                                usd_value = self.get_usd_value(asset, amounts, exchange)
                                total_usd_value += usd_value
                                
                                # Guardar en base de datos
                                balance_record = Balance()
                                balance_record.asset = asset
                                balance_record.free_balance = balance_data['free'].get(asset, 0)
                                balance_record.locked_balance = balance_data['used'].get(asset, 0)
                                balance_record.total_balance = amounts
                                balance_record.usd_value = usd_value
                                balance_record.exchange = exchange.upper()
                                db.session.add(balance_record)
                
                db.session.commit()
                logging.info(f"Balances updated: ${total_usd_value:.2f} total")
                
        except Exception as e:
            logging.error(f"Error updating balances: {e}")
    
    def get_usd_value(self, asset, amount, exchange):
        """Obtener valor USD de un asset"""
        if asset in ['USDT', 'USD', 'USDC']:
            return amount
        
        try:
            symbol = f'{asset}/USDT'
            ticker = self.run_ccxt_command('fetch_ticker', exchange, symbol)
            if ticker and 'last' in ticker:
                return amount * ticker['last']
        except:
            pass
        
        return 0
    
    def scan_arbitrage_opportunities(self):
        """Escanear oportunidades de arbitraje entre exchanges"""
        try:
            for symbol in self.target_symbols:
                prices = {}
                
                # Obtener precios de todos los exchanges
                for exchange in self.exchanges:
                    ticker = self.run_ccxt_command('fetch_ticker', exchange, symbol)
                    if ticker and 'bid' in ticker and 'ask' in ticker:
                        prices[exchange] = {
                            'bid': ticker['bid'],
                            'ask': ticker['ask'],
                            'last': ticker['last']
                        }
                
                # Buscar oportunidades
                if len(prices) >= 2:
                    self.find_arbitrage_opportunity(symbol, prices)
                    
        except Exception as e:
            logging.error(f"Error scanning opportunities: {e}")
    
    def find_arbitrage_opportunity(self, symbol, prices):
        """Buscar y ejecutar oportunidad de arbitraje"""
        best_opportunity = None
        max_spread = 0
        
        for buy_exchange, buy_data in prices.items():
            for sell_exchange, sell_data in prices.items():
                if buy_exchange != sell_exchange:
                    spread = (sell_data['bid'] - buy_data['ask']) / buy_data['ask']
                    
                    if spread > self.target_spread and spread > max_spread:
                        max_spread = spread
                        best_opportunity = {
                            'symbol': symbol,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'buy_price': buy_data['ask'],
                            'sell_price': sell_data['bid'],
                            'spread_percentage': spread * 100,
                            'potential_profit': self.min_trade_amount * spread
                        }
        
        if best_opportunity:
            logging.info(f"Opportunity found: {best_opportunity}")
            self.execute_arbitrage(best_opportunity)
    
    def execute_arbitrage(self, opportunity):
        """Ejecutar operación de arbitraje"""
        try:
            symbol = opportunity['symbol']
            trade_amount = self.min_trade_amount
            
            # Verificar balance disponible
            if not self.has_sufficient_balance('USDT', trade_amount, opportunity['buy_exchange']):
                logging.warning(f"Insufficient USDT balance for {opportunity['buy_exchange']}")
                return
            
            # Ejecutar compra
            buy_order = self.run_ccxt_command(
                'create_market_buy_order',
                opportunity['buy_exchange'],
                symbol,
                f'"{trade_amount}"'
            )
            
            if buy_order and buy_order.get('status') == 'closed':
                # Registrar trade de compra
                self.record_trade(
                    symbol=symbol,
                    side='BUY',
                    quantity=buy_order['filled'],
                    price=buy_order['average'],
                    total_value=trade_amount,
                    exchange=opportunity['buy_exchange'],
                    order_id=buy_order['id']
                )
                
                # Guardar posición para venta posterior
                position_id = f"{symbol}_{int(time.time())}"
                self.positions[position_id] = {
                    'symbol': symbol,
                    'quantity': buy_order['filled'],
                    'buy_price': buy_order['average'],
                    'buy_exchange': opportunity['buy_exchange'],
                    'sell_exchange': opportunity['sell_exchange'],
                    'timestamp': time.time()
                }
                
                logging.info(f"Arbitrage buy executed: {symbol} on {opportunity['buy_exchange']}")
                
        except Exception as e:
            logging.error(f"Error executing arbitrage: {e}")
    
    def has_sufficient_balance(self, asset, amount, exchange):
        """Verificar si hay balance suficiente"""
        try:
            balance = Balance.query.filter_by(
                asset=asset, 
                exchange=exchange.upper()
            ).first()
            return balance and balance.free_balance >= amount
        except:
            return False
    
    def record_trade(self, symbol, side, quantity, price, total_value, exchange, order_id):
        """Registrar trade en base de datos"""
        try:
            trade = Trade()
            trade.symbol = symbol
            trade.side = side
            trade.quantity = quantity
            trade.price = price
            trade.total_value = total_value
            trade.strategy = 'arbitrage_ccxt'
            trade.exchange = exchange.upper()
            trade.order_id = order_id
            
            db.session.add(trade)
            db.session.commit()
            
        except Exception as e:
            logging.error(f"Error recording trade: {e}")
    
    def manage_positions(self):
        """Gestionar posiciones abiertas"""
        positions_to_close = []
        current_time = time.time()
        
        for pos_id, position in self.positions.items():
            try:
                # Obtener precio actual
                ticker = self.run_ccxt_command(
                    'fetch_ticker',
                    position['sell_exchange'],
                    position['symbol']
                )
                
                if ticker and 'bid' in ticker:
                    current_price = ticker['bid']
                    profit_pct = (current_price - position['buy_price']) / position['buy_price']
                    
                    # Criterios para cerrar posición
                    should_close = False
                    reason = ""
                    
                    if profit_pct >= 0.008:  # 0.8% ganancia
                        should_close = True
                        reason = "PROFIT_TARGET"
                    elif profit_pct <= -self.stop_loss_percentage:
                        should_close = True
                        reason = "STOP_LOSS"
                    elif current_time - position['timestamp'] > 600:  # 10 minutos max
                        should_close = True
                        reason = "TIME_EXIT"
                    
                    if should_close:
                        self.close_position(position, current_price, reason)
                        positions_to_close.append(pos_id)
                        
            except Exception as e:
                logging.error(f"Error managing position {pos_id}: {e}")
        
        # Remover posiciones cerradas
        for pos_id in positions_to_close:
            del self.positions[pos_id]
    
    def close_position(self, position, current_price, reason):
        """Cerrar posición vendiendo"""
        try:
            sell_order = self.run_ccxt_command(
                'create_market_sell_order',
                position['sell_exchange'],
                position['symbol'],
                position['quantity']
            )
            
            if sell_order and sell_order.get('status') == 'closed':
                profit_loss = (sell_order['average'] - position['buy_price']) * position['quantity']
                
                # Registrar trade de venta
                trade = Trade()
                trade.symbol = position['symbol']
                trade.side = 'SELL'
                trade.quantity = position['quantity']
                trade.price = sell_order['average']
                trade.total_value = sell_order['cost']
                trade.profit_loss = profit_loss
                trade.strategy = 'arbitrage_ccxt'
                trade.exchange = position['sell_exchange'].upper()
                trade.order_id = sell_order['id']
                
                db.session.add(trade)
                db.session.commit()
                
                logging.info(f"Position closed: {position['symbol']} - P/L: ${profit_loss:.2f} - Reason: {reason}")
                
        except Exception as e:
            logging.error(f"Error closing position: {e}")
    
    def create_alert(self, title, message, alert_type):
        """Crear alerta del sistema"""
        try:
            alert = Alert()
            alert.title = title
            alert.message = message
            alert.alert_type = alert_type
            
            db.session.add(alert)
            db.session.commit()
            
            logging.info(f"Alert created: {title}")
            
        except Exception as e:
            logging.error(f"Error creating alert: {e}")
    
    def stop(self):
        """Detener motor de trading"""
        self.is_running = False
        logging.info("Enhanced Trading Engine stopped")