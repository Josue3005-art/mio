import subprocess
import json
import logging
import time
import asyncio
from datetime import datetime
from app import db
from models import Trade, Alert, DailyStats

class StableTradingBot:
    """Bot de trading estable sin timeouts"""
    
    def __init__(self):
        self.exchanges = ['gate', 'mexc', 'okx', 'bitget']
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        self.min_spread = 0.003  # 0.3% mínimo
        self.capital = 30.0
        self.is_running = False
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_price_data(self, exchange, symbol):
        """Obtener datos de precio de un exchange"""
                result = subprocess.run(
                ["node", "/home/ubuntu/binance_miner_analysis/BinanceMiner/get_price.js", exchange, symbol],
                capture_output=True,
                text=True,
                timeout=8
            )    
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting price data: {e}")
            return None
    
    def scan_arbitrage_opportunities(self):
        """Escanear oportunidades de arbitraje"""
        opportunities = []
        
        for symbol in self.symbols:
            prices = {}
            
            # Obtener precios de todos los exchanges
            for exchange in self.exchanges:
                price_data = self.get_price_data(exchange, symbol)
                if price_data and not 'error' in price_data:
                    prices[exchange] = price_data
            
            # Buscar oportunidades
            for buy_ex in prices:
                for sell_ex in prices:
                    if buy_ex != sell_ex:
                        buy_price = prices[buy_ex]['ask']
                        sell_price = prices[sell_ex]['bid']
                        spread = (sell_price - buy_price) / buy_price
                        
                        if spread > self.min_spread:
                            opportunity = {
                                'symbol': symbol,
                                'buy_exchange': buy_ex,
                                'sell_exchange': sell_ex,
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'spread_percentage': spread * 100,
                                'potential_profit': self.capital * spread * 0.8,  # 80% del capital
                                'timestamp': datetime.now()
                            }
                            opportunities.append(opportunity)
        
        # Ordenar por mayor spread
        opportunities.sort(key=lambda x: x['spread_percentage'], reverse=True)
        return opportunities[:3]  # Top 3 oportunidades
    
    def create_alert_record(self, title, message, alert_type):
        """Crear registro de alerta"""
        try:
            alert = Alert()
            alert.title = title
            alert.message = message
            alert.alert_type = alert_type
            
            db.session.add(alert)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error creating alert: {e}")
    
    def simulate_trade_execution(self, opportunity):
        """Simular ejecución de trade (modo seguro)"""
        try:
            # Simular compra
            trade_amount = min(self.capital * 0.4, 12.0)  # Máximo 40% del capital o $12
            quantity = trade_amount / opportunity['buy_price']
            
            # Registrar trade simulado
            trade = Trade()
            trade.symbol = opportunity['symbol']
            trade.side = 'BUY'
            trade.quantity = quantity
            trade.price = opportunity['buy_price']
            trade.total_value = trade_amount
            trade.fee = trade_amount * 0.001
            trade.strategy = 'arbitrage_simulation'
            trade.exchange = opportunity['buy_exchange'].upper()
            trade.order_id = f"SIM_{int(time.time())}"
            
            db.session.add(trade)
            
            # Simular venta inmediata
            sell_total = quantity * opportunity['sell_price']
            profit = sell_total - trade_amount - (sell_total * 0.001)
            
            sell_trade = Trade()
            sell_trade.symbol = opportunity['symbol']
            sell_trade.side = 'SELL'
            sell_trade.quantity = quantity
            sell_trade.price = opportunity['sell_price']
            sell_trade.total_value = sell_total
            sell_trade.fee = sell_total * 0.001
            sell_trade.profit_loss = profit
            sell_trade.strategy = 'arbitrage_simulation'
            sell_trade.exchange = opportunity['sell_exchange'].upper()
            sell_trade.order_id = f"SIM_{int(time.time()) + 1}"
            
            db.session.add(sell_trade)
            db.session.commit()
            
            self.logger.info(f"Simulated arbitrage: {opportunity['symbol']} - Profit: ${profit:.4f}")
            
            # Crear alerta de oportunidad
            self.create_alert_record(
                "Arbitrage Opportunity",
                f"{opportunity['symbol']}: {opportunity['buy_exchange']} → {opportunity['sell_exchange']} | Spread: {opportunity['spread_percentage']:.3f}% | Profit: ${profit:.4f}",
                "SUCCESS"
            )
            
        except Exception as e:
            self.logger.error(f"Error simulating trade: {e}")
    
    def update_daily_stats(self):
        """Actualizar estadísticas diarias"""
        try:
            today = datetime.now().date()
            
            # Obtener trades de hoy
            today_trades = Trade.query.filter(
                Trade.executed_at >= datetime.combine(today, datetime.min.time())
            ).all()
            
            if today_trades:
                total_profit = sum(t.profit_loss for t in today_trades if t.profit_loss)
                total_trades = len(today_trades)
                successful_trades = len([t for t in today_trades if t.profit_loss and t.profit_loss > 0])
                
                # Actualizar o crear estadísticas
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
            self.logger.error(f"Error updating daily stats: {e}")
    
    def run_single_scan(self):
        """Ejecutar un escaneo único"""
        try:
            self.logger.info("Scanning for arbitrage opportunities...")
            
            opportunities = self.scan_arbitrage_opportunities()
            
            if opportunities:
                self.logger.info(f"Found {len(opportunities)} opportunities")
                
                # Ejecutar la mejor oportunidad
                best_opportunity = opportunities[0]
                if best_opportunity['spread_percentage'] > 0.3:  # Mínimo 0.3%
                    self.simulate_trade_execution(best_opportunity)
                    
                # Alertar sobre todas las oportunidades
                for opp in opportunities:
                    self.logger.info(f"Opportunity: {opp['symbol']} {opp['buy_exchange']}→{opp['sell_exchange']} {opp['spread_percentage']:.3f}%")
            else:
                self.logger.info("No significant opportunities found")
            
            # Actualizar estadísticas
            self.update_daily_stats()
            
        except Exception as e:
            self.logger.error(f"Error in scan: {e}")
            
        return len(opportunities) if opportunities else 0

# Instancia global del bot
trading_bot = StableTradingBot()