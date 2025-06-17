import time
import logging
from datetime import datetime, timedelta
from app import db
from flask_socketio import emit
from models import Trade, Balance, DailyStats, TradingConfig, Alert
from exchange_simulator import ExchangeSimulator
import threading

class SimpleTradingEngine:
    def __init__(self, telegram_bot=None):
        # Use simulator for now to get the app running
        self.client = ExchangeSimulator("Binance")
        self.kucoin_client = ExchangeSimulator("KuCoin")
        self.telegram_bot = telegram_bot
        
        # Trading parameters
        self.min_trade_amount = 5.0
        self.max_trade_amount = 15.0
        self.stop_loss_percentage = 0.02
        self.target_spread = 0.005
        self.reinvestment_rate = 0.8
        
        self.is_running = False
        self.positions = {}
        
        # Target symbols for arbitrage
        self.target_symbols = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT',
            'LTCUSDT', 'XLMUSDT', 'VETUSDT', 'TRXUSDT', 'EOSUSDT'
        ]
        
        logging.info("Simple Trading Engine initialized")

    def start(self):
        """Start the trading engine"""
        self.is_running = True
        logging.info("Starting Simple Trading Engine...")
        
        while self.is_running:
            try:
                self.update_balances()
                self.scan_opportunities()
                self.manage_positions()
                self.update_daily_stats()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logging.error(f"Error in trading loop: {e}")
                self.create_alert("Trading Error", f"Error in main loop: {str(e)}", "ERROR")
                time.sleep(10)

    def update_balances(self):
        """Update account balances from simulator"""
        try:
            account_info = self.client.get_account()
            if not account_info:
                return
            
            total_usd_value = 0
            
            with db.session.begin():
                # Clear existing balances
                Balance.query.delete()
                
                for balance in account_info['balances']:
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        usd_value = self.get_usd_value(balance['asset'], total)
                        total_usd_value += usd_value
                        
                        balance_record = Balance()
                        balance_record.asset = balance['asset']
                        balance_record.free_balance = free
                        balance_record.locked_balance = locked
                        balance_record.total_balance = total
                        balance_record.usd_value = usd_value
                        db.session.add(balance_record)
                
                db.session.commit()
            
            # No socket emission needed from here
            
        except Exception as e:
            logging.error(f"Error updating balances: {e}")

    def get_usd_value(self, asset, amount):
        """Get USD value of an asset"""
        if asset == 'USDT':
            return amount
        
        try:
            symbol = f'{asset}USDT'
            ticker = self.client.get_symbol_ticker(symbol)
            if ticker and 'price' in ticker:
                return amount * float(ticker['price'])
        except:
            pass
        
        return 0

    def scan_opportunities(self):
        """Scan for arbitrage opportunities between exchanges"""
        try:
            for symbol in self.target_symbols:
                # Get prices from both exchanges
                binance_book = self.client.get_order_book(symbol)
                kucoin_book = self.kucoin_client.get_order_book(symbol)
                
                if not binance_book or not kucoin_book:
                    continue
                
                # Calculate spread between exchanges
                binance_ask = float(binance_book['asks'][0][0])
                binance_bid = float(binance_book['bids'][0][0])
                kucoin_ask = float(kucoin_book['asks'][0][0])
                kucoin_bid = float(kucoin_book['bids'][0][0])
                
                # Find arbitrage opportunity
                if binance_bid > kucoin_ask:
                    # Buy on KuCoin, sell on Binance
                    spread = (binance_bid - kucoin_ask) / kucoin_ask
                    if spread > self.target_spread:
                        opportunity = {
                            'symbol': symbol,
                            'buy_exchange': 'KuCoin',
                            'sell_exchange': 'Binance',
                            'buy_price': kucoin_ask,
                            'sell_price': binance_bid,
                            'spread_percentage': spread,
                            'potential_profit': self.min_trade_amount * spread
                        }
                        self.execute_arbitrage_opportunity(opportunity)
                
                elif kucoin_bid > binance_ask:
                    # Buy on Binance, sell on KuCoin
                    spread = (kucoin_bid - binance_ask) / binance_ask
                    if spread > self.target_spread:
                        opportunity = {
                            'symbol': symbol,
                            'buy_exchange': 'Binance',
                            'sell_exchange': 'KuCoin',
                            'buy_price': binance_ask,
                            'sell_price': kucoin_bid,
                            'spread_percentage': spread,
                            'potential_profit': self.min_trade_amount * spread
                        }
                        self.execute_arbitrage_opportunity(opportunity)
                        
        except Exception as e:
            logging.error(f"Error scanning opportunities: {e}")

    def execute_arbitrage_opportunity(self, opportunity):
        """Execute an arbitrage opportunity"""
        try:
            symbol = opportunity['symbol']
            trade_amount = self.min_trade_amount
            
            # Check if we have enough balance
            usdt_balance = self.get_asset_balance('USDT')
            if usdt_balance < trade_amount:
                return
            
            # Execute buy order on cheaper exchange
            buy_client = self.client if opportunity['buy_exchange'] == 'Binance' else self.kucoin_client
            buy_order = buy_client.order_market_buy(symbol, trade_amount)
            
            if buy_order and buy_order.get('status') == 'FILLED':
                # Record buy trade
                trade = Trade()
                trade.symbol = symbol
                trade.side = 'BUY'
                trade.quantity = float(buy_order['executedQty'])
                trade.price = float(buy_order['fills'][0]['price'])
                trade.total_value = trade_amount
                trade.fee = float(buy_order['fills'][0]['commission'])
                trade.strategy = 'arbitrage'
                trade.exchange = opportunity['buy_exchange']
                trade.order_id = buy_order['orderId']
                
                db.session.add(trade)
                db.session.commit()
                
                # Store position for selling
                self.positions[f"{symbol}_{int(time.time())}"] = {
                    'symbol': symbol,
                    'quantity': float(buy_order['executedQty']),
                    'buy_price': float(buy_order['fills'][0]['price']),
                    'buy_exchange': opportunity['buy_exchange'],
                    'sell_exchange': opportunity['sell_exchange'],
                    'timestamp': time.time()
                }
                
                logging.info(f"Arbitrage buy executed: {symbol} on {opportunity['buy_exchange']}")
                
                # Log trade notification
                logging.info(f"Trade executed: {symbol} BUY ${trade_amount} at {trade.price}")
                
        except Exception as e:
            logging.error(f"Error executing arbitrage: {e}")

    def manage_positions(self):
        """Manage open positions"""
        positions_to_remove = []
        current_time = time.time()
        
        for pos_id, position in self.positions.items():
            try:
                symbol = position['symbol']
                
                # Get current price
                ticker = self.client.get_symbol_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = float(ticker['price'])
                buy_price = position['buy_price']
                quantity = position['quantity']
                
                # Calculate profit percentage
                profit_pct = (current_price - buy_price) / buy_price
                
                # Check if we should sell (profit target or time-based)
                should_sell = False
                reason = ""
                
                if profit_pct >= 0.008:  # 0.8% profit target
                    should_sell = True
                    reason = "PROFIT_TARGET"
                elif profit_pct <= -self.stop_loss_percentage:  # Stop loss
                    should_sell = True
                    reason = "STOP_LOSS"
                elif current_time - position['timestamp'] > 300:  # 5 minutes max hold
                    should_sell = True
                    reason = "TIME_EXIT"
                
                if should_sell:
                    self.execute_sell_position(position, current_price, reason)
                    positions_to_remove.append(pos_id)
                    
            except Exception as e:
                logging.error(f"Error managing position {pos_id}: {e}")
        
        # Remove closed positions
        for pos_id in positions_to_remove:
            del self.positions[pos_id]

    def execute_sell_position(self, position, current_price, reason):
        """Execute sell order for a position"""
        try:
            symbol = position['symbol']
            quantity = position['quantity']
            
            # Execute sell on the target exchange
            sell_client = self.kucoin_client if position['sell_exchange'] == 'KuCoin' else self.client
            sell_order = sell_client.order_market_sell(symbol, quantity)
            
            if sell_order and sell_order.get('status') == 'FILLED':
                executed_price = float(sell_order['fills'][0]['price'])
                total_value = quantity * executed_price
                
                # Calculate profit/loss
                buy_total = quantity * position['buy_price']
                profit_loss = total_value - buy_total
                
                # Record sell trade
                trade = Trade()
                trade.symbol = symbol
                trade.side = 'SELL'
                trade.quantity = quantity
                trade.price = executed_price
                trade.total_value = total_value
                trade.fee = float(sell_order['fills'][0]['commission'])
                trade.strategy = 'arbitrage'
                trade.profit_loss = profit_loss
                trade.exchange = position['sell_exchange']
                trade.order_id = sell_order['orderId']
                
                db.session.add(trade)
                db.session.commit()
                
                logging.info(f"Position closed: {symbol} - P/L: ${profit_loss:.2f} - Reason: {reason}")
                
                # Log trade notification
                logging.info(f"Position closed: {symbol} SELL - P/L: ${profit_loss:.2f} - Reason: {reason}")
                
        except Exception as e:
            logging.error(f"Error executing sell: {e}")

    def get_asset_balance(self, asset):
        """Get balance for a specific asset"""
        try:
            balance = Balance.query.filter_by(asset=asset).first()
            return balance.free_balance if balance else 0
        except:
            return 0

    def update_daily_stats(self):
        """Update daily trading statistics"""
        try:
            today = datetime.now().date()
            
            stats = DailyStats.query.filter_by(date=today).first()
            if not stats:
                yesterday = today - timedelta(days=1)
                yesterday_stats = DailyStats.query.filter_by(date=yesterday).first()
                starting_balance = yesterday_stats.ending_balance if yesterday_stats else 30.0
                
                stats = DailyStats()
                stats.date = today
                stats.starting_balance = starting_balance
                stats.ending_balance = starting_balance
                db.session.add(stats)
            
            # Update statistics from today's trades
            today_trades = Trade.query.filter(
                Trade.executed_at >= datetime.combine(today, datetime.min.time())
            ).all()
            
            stats.total_trades = len(today_trades)
            stats.successful_trades = len([t for t in today_trades if t.profit_loss and t.profit_loss > 0])
            stats.total_profit = sum(t.profit_loss for t in today_trades if t.profit_loss)
            stats.total_fees = sum(t.fee for t in today_trades)
            
            # Get current balance
            current_balance = sum(b.usd_value for b in Balance.query.all())
            stats.ending_balance = current_balance
            
            if stats.starting_balance > 0:
                stats.roi_percentage = ((stats.ending_balance - stats.starting_balance) / stats.starting_balance) * 100
            
            db.session.commit()
            
        except Exception as e:
            logging.error(f"Error updating daily stats: {e}")

    def create_alert(self, title, message, alert_type):
        """Create a system alert"""
        try:
            alert = Alert()
            alert.title = title
            alert.message = message
            alert.alert_type = alert_type
            
            db.session.add(alert)
            db.session.commit()
            
            # Log alert
            logging.info(f"Alert created: {title} - {message}")
            
        except Exception as e:
            logging.error(f"Error creating alert: {e}")

    def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        logging.info("Simple Trading Engine stopped")