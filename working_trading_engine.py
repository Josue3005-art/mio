import subprocess
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from app import db
from models import Trade, Balance, DailyStats, Alert

class WorkingTradingEngine:
    """Motor de trading funcionando con exchanges disponibles"""
    
    def __init__(self, telegram_bot=None):
        self.telegram_bot = telegram_bot
        self.is_running = False
        self.positions = {}
        
        # Configuración optimizada para capital de $30
        self.min_trade_amount = 5.0
        self.max_trade_amount = 12.0  
        self.target_spread = 0.002  # 0.2% mínimo
        self.stop_loss_percentage = 0.015  # 1.5% stop loss
        self.take_profit_percentage = 0.008  # 0.8% take profit
        
        # Exchanges que funcionan desde esta ubicación
        self.exchanges = ['gate', 'mexc']
        self.target_symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        
        logging.info("Working Trading Engine initialized with available exchanges")
    
    def run_ccxt_command(self, command, exchange, symbol=None, amount=None):
        """Ejecutar comando CCXT con exchanges disponibles"""
        try:
            script = f"""
const ccxt = require('ccxt');

async function execute() {{
    try {{
        const exchange = new ccxt.{exchange}({{
            sandbox: false,
            enableRateLimit: true,
        }});
        
        let result;
        switch ('{command}') {{
            case 'fetch_ticker':
                result = await exchange.fetchTicker('{symbol or "BTC/USDT"}');
                break;
            case 'fetch_order_book':
                result = await exchange.fetchOrderBook('{symbol or "BTC/USDT"}', 10);
                break;
            case 'fetch_markets':
                result = await exchange.loadMarkets();
                break;
            case 'test_connection':
                result = await exchange.fetchTicker('BTC/USDT');
                result = {{ success: true, price: result.last }};
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
            
            with open('/tmp/ccxt_script.js', 'w') as f:
                f.write(script)
            
            result = subprocess.run(
                ['node', '/tmp/ccxt_script.js'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logging.error(f"CCXT error: {result.stderr}")
                return None
                
        except Exception as e:
            logging.error(f"Error running CCXT command: {e}")
            return None
    
    def start(self):
        """Iniciar motor de trading"""
        self.is_running = True
        logging.info("Starting Working Trading Engine...")
        
        # Verificar conexiones iniciales
        self.test_connections()
        
        while self.is_running:
            try:
                self.scan_arbitrage_opportunities()
                self.manage_positions()
                self.update_trading_stats()
                
                time.sleep(15)  # Revisar cada 15 segundos
                
            except Exception as e:
                logging.error(f"Error in trading loop: {e}")
                time.sleep(30)
    
    def test_connections(self):
        """Probar conexiones a exchanges"""
        for exchange in self.exchanges:
            result = self.run_ccxt_command('test_connection', exchange)
            if result and 'success' in result:
                logging.info(f"✅ {exchange.upper()} connected - BTC: ${result['price']}")
                self.create_alert("Exchange Connected", f"{exchange.upper()} API working - BTC: ${result['price']}", "SUCCESS")
            else:
                logging.error(f"❌ {exchange.upper()} connection failed")
                self.create_alert("Exchange Error", f"Failed to connect to {exchange.upper()}", "ERROR")
    
    def scan_arbitrage_opportunities(self):
        """Escanear oportunidades de arbitraje"""
        try:
            for symbol in self.target_symbols:
                prices = {}
                
                # Obtener precios de exchanges disponibles
                for exchange in self.exchanges:
                    ticker = self.run_ccxt_command('fetch_ticker', exchange, symbol)
                    if ticker and 'bid' in ticker and 'ask' in ticker:
                        prices[exchange] = {
                            'bid': ticker['bid'],
                            'ask': ticker['ask'],
                            'last': ticker['last'],
                            'volume': ticker.get('baseVolume', 0)
                        }
                
                # Analizar oportunidades
                if len(prices) >= 2:
                    self.analyze_arbitrage_opportunity(symbol, prices)
                    
        except Exception as e:
            logging.error(f"Error scanning opportunities: {e}")
    
    def analyze_arbitrage_opportunity(self, symbol, prices):
        """Analizar y ejecutar oportunidad de arbitraje"""
        best_opportunity = None
        max_spread = 0
        
        exchanges = list(prices.keys())
        for i in range(len(exchanges)):
            for j in range(len(exchanges)):
                if i != j:
                    buy_exchange = exchanges[i]
                    sell_exchange = exchanges[j]
                    
                    buy_price = prices[buy_exchange]['ask']
                    sell_price = prices[sell_exchange]['bid']
                    spread = (sell_price - buy_price) / buy_price
                    
                    # Verificar volumen suficiente
                    min_volume = 100  # Volumen mínimo requerido
                    if (spread > self.target_spread and 
                        spread > max_spread and
                        prices[buy_exchange]['volume'] > min_volume and
                        prices[sell_exchange]['volume'] > min_volume):
                        
                        max_spread = spread
                        best_opportunity = {
                            'symbol': symbol,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'spread_percentage': spread * 100,
                            'potential_profit': self.min_trade_amount * spread
                        }
        
        if best_opportunity:
            logging.info(f"Arbitrage opportunity found: {symbol} - {best_opportunity['spread_percentage']:.3f}% spread")
            self.simulate_arbitrage_execution(best_opportunity)
    
    def simulate_arbitrage_execution(self, opportunity):
        """Simular ejecución de arbitraje (para demostración segura)"""
        try:
            symbol = opportunity['symbol']
            trade_amount = self.min_trade_amount
            
            # Simular compra
            buy_price = opportunity['buy_price']
            quantity = trade_amount / buy_price
            
            # Registrar trade simulado de compra
            buy_trade = Trade()
            buy_trade.symbol = symbol
            buy_trade.side = 'BUY'
            buy_trade.quantity = quantity
            buy_trade.price = buy_price
            buy_trade.total_value = trade_amount
            buy_trade.fee = trade_amount * 0.001  # 0.1% fee
            buy_trade.strategy = 'arbitrage_simulation'
            buy_trade.exchange = opportunity['buy_exchange'].upper()
            buy_trade.order_id = f"SIM_{int(time.time())}"
            
            db.session.add(buy_trade)
            
            # Crear posición para venta
            position_id = f"{symbol}_{int(time.time())}"
            self.positions[position_id] = {
                'symbol': symbol,
                'quantity': quantity,
                'buy_price': buy_price,
                'buy_exchange': opportunity['buy_exchange'],
                'sell_exchange': opportunity['sell_exchange'],
                'target_sell_price': opportunity['sell_price'],
                'timestamp': time.time(),
                'trade_id': buy_trade.order_id
            }
            
            db.session.commit()
            
            logging.info(f"Simulated arbitrage buy: {symbol} - ${trade_amount} at ${buy_price}")
            
            # Crear alerta de oportunidad
            self.create_alert(
                "Arbitrage Opportunity",
                f"{symbol}: Buy {opportunity['buy_exchange']} ${buy_price:.2f} → Sell {opportunity['sell_exchange']} ${opportunity['sell_price']:.2f} (Spread: {opportunity['spread_percentage']:.3f}%)",
                "INFO"
            )
            
        except Exception as e:
            logging.error(f"Error simulating arbitrage: {e}")
    
    def manage_positions(self):
        """Gestionar posiciones abiertas"""
        positions_to_close = []
        current_time = time.time()
        
        for pos_id, position in self.positions.items():
            try:
                # Obtener precio actual en exchange de venta
                ticker = self.run_ccxt_command('fetch_ticker', position['sell_exchange'], position['symbol'])
                
                if ticker and 'bid' in ticker:
                    current_sell_price = ticker['bid']
                    buy_price = position['buy_price']
                    profit_pct = (current_sell_price - buy_price) / buy_price
                    
                    should_close = False
                    reason = ""
                    
                    # Criterios para cerrar posición
                    if profit_pct >= self.take_profit_percentage:
                        should_close = True
                        reason = "PROFIT_TARGET"
                    elif profit_pct <= -self.stop_loss_percentage:
                        should_close = True
                        reason = "STOP_LOSS"
                    elif current_time - position['timestamp'] > 900:  # 15 minutos máximo
                        should_close = True
                        reason = "TIME_EXIT"
                    
                    if should_close:
                        self.close_position_simulation(position, current_sell_price, reason)
                        positions_to_close.append(pos_id)
                        
            except Exception as e:
                logging.error(f"Error managing position {pos_id}: {e}")
        
        # Remover posiciones cerradas
        for pos_id in positions_to_close:
            del self.positions[pos_id]
    
    def close_position_simulation(self, position, sell_price, reason):
        """Simular cierre de posición"""
        try:
            quantity = position['quantity']
            sell_total = quantity * sell_price
            buy_total = quantity * position['buy_price']
            profit_loss = sell_total - buy_total - (sell_total * 0.001)  # Menos fees
            
            # Registrar trade de venta simulado
            sell_trade = Trade()
            sell_trade.symbol = position['symbol']
            sell_trade.side = 'SELL'
            sell_trade.quantity = quantity
            sell_trade.price = sell_price
            sell_trade.total_value = sell_total
            sell_trade.fee = sell_total * 0.001
            sell_trade.profit_loss = profit_loss
            sell_trade.strategy = 'arbitrage_simulation'
            sell_trade.exchange = position['sell_exchange'].upper()
            sell_trade.order_id = f"SIM_{int(time.time())}"
            
            db.session.add(sell_trade)
            db.session.commit()
            
            profit_pct = (profit_loss / (quantity * position['buy_price'])) * 100
            
            logging.info(f"Position closed: {position['symbol']} - P/L: ${profit_loss:.4f} ({profit_pct:.3f}%) - Reason: {reason}")
            
            # Crear alerta de resultado
            alert_type = "SUCCESS" if profit_loss > 0 else "WARNING"
            self.create_alert(
                "Position Closed",
                f"{position['symbol']}: {reason} - P/L: ${profit_loss:.4f} ({profit_pct:.3f}%)",
                alert_type
            )
            
        except Exception as e:
            logging.error(f"Error closing position: {e}")
    
    def update_trading_stats(self):
        """Actualizar estadísticas de trading"""
        try:
            today = datetime.now().date()
            
            # Obtener estadísticas del día
            today_trades = Trade.query.filter(
                Trade.executed_at >= datetime.combine(today, datetime.min.time())
            ).all()
            
            if today_trades:
                total_profit = sum(t.profit_loss for t in today_trades if t.profit_loss)
                total_trades = len(today_trades)
                successful_trades = len([t for t in today_trades if t.profit_loss and t.profit_loss > 0])
                
                # Actualizar estadísticas diarias
                stats = DailyStats.query.filter_by(date=today).first()
                if not stats:
                    stats = DailyStats()
                    stats.date = today
                    stats.starting_balance = 30.0
                    db.session.add(stats)
                
                stats.total_trades = total_trades
                stats.successful_trades = successful_trades
                stats.total_profit = total_profit
                stats.ending_balance = 30.0 + total_profit
                
                if stats.starting_balance > 0:
                    stats.roi_percentage = (total_profit / stats.starting_balance) * 100
                
                db.session.commit()
                
        except Exception as e:
            logging.error(f"Error updating stats: {e}")
    
    def create_alert(self, title, message, alert_type):
        """Crear alerta del sistema"""
        try:
            alert = Alert()
            alert.title = title
            alert.message = message
            alert.alert_type = alert_type
            
            db.session.add(alert)
            db.session.commit()
            
            logging.info(f"Alert: {title}")
            
        except Exception as e:
            logging.error(f"Error creating alert: {e}")
    
    def get_status(self):
        """Obtener estado del motor"""
        return {
            'running': self.is_running,
            'exchanges': self.exchanges,
            'active_positions': len(self.positions),
            'target_symbols': self.target_symbols
        }
    
    def stop(self):
        """Detener motor de trading"""
        self.is_running = False
        logging.info("Working Trading Engine stopped")