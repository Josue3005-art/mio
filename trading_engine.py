import asyncio
import time
import logging
import os
from datetime import datetime, timedelta
from app import db, socketio
from models import Trade, Balance, DailyStats, TradingConfig, Alert
from arbitrage_scanner import ArbitrageScanner
from risk_manager import RiskManager
from binance_client import BinanceClient
from kucoin_client import KuCoinClient
import threading

class TradingEngine:
    def __init__(self, telegram_bot=None):
        # Use hardcoded API keys for testing
        self.api_key = '2LMbgTKIlWhHBArycKAIyhEnCAM0OIA2rZGgkNYjaZXPag4BD5bAlnqzFWsARdV8'
        self.api_secret = 'cJItjpwD8ik5Adt9x2ecSjKPZv1BMrktaJnZbK0s7evCPNbtd5OwYropznenXItk'
        self.telegram_bot = telegram_bot
        
        if not self.api_key or not self.api_secret:
            logging.error("Binance API credentials not found")
            raise ValueError("Missing Binance API credentials")
        
        self.client = BinanceClient(self.api_key, self.api_secret)
        
        # Initialize KuCoin client
        self.kucoin_client = KuCoinClient(
            '6843964c6025980001ef7b55',
            '3e67acf6-a77d-462d-a19f-4a9f75057c4e',
            'AA290523'
        )
        self.arbitrage_scanner = ArbitrageScanner(self.client)
        self.risk_manager = RiskManager()
        
        # Trading parameters
        self.min_trade_amount = 5.0  # Minimum $5 per trade
        self.max_trade_amount = 15.0  # Maximum $15 per trade
        self.stop_loss_percentage = 0.02  # 2% stop loss
        self.target_spread = 0.005  # 0.5% minimum spread
        self.reinvestment_rate = 0.8  # Reinvest 80% of profits
        
        self.is_running = False
        self.positions = {}
        
        logging.info("Trading Engine initialized successfully")

    def start(self):
        """Start the trading engine"""
        self.is_running = True
        logging.info("Starting Trading Engine...")
        
        # Start main trading loop
        while self.is_running:
            try:
                self.update_balances()
                self.scan_opportunities()
                self.manage_positions()
                self.update_daily_stats()
                
                time.sleep(1)  # Short delay for high-frequency trading
                
            except Exception as e:
                logging.error(f"Error in trading loop: {e}")
                self.create_alert("Trading Error", f"Error in main loop: {str(e)}", "ERROR")
                time.sleep(5)  # Wait longer on error

    def update_balances(self):
        """Update account balances"""
        try:
            account_info = self.client.get_account()
            total_usd_value = 0
            
            with db.session.begin():
                # Clear existing balances
                Balance.query.delete()
                
                for balance in account_info['balances']:
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        # Get USD value
                        usd_value = self.get_usd_value(balance['asset'], total)
                        total_usd_value += usd_value
                        
                        # Save to database
                        balance_record = Balance()
                        balance_record.asset = balance['asset']
                        balance_record.free_balance = free
                        balance_record.locked_balance = locked
                        balance_record.total_balance = total
                        balance_record.usd_value = usd_value
                        db.session.add(balance_record)
                
                db.session.commit()
            
            # Emit balance update via WebSocket
            socketio.emit('balance_update', {'total_usd': total_usd_value})
            
        except Exception as e:
            logging.error(f"Error updating balances: {e}")

    def get_usd_value(self, asset, amount):
        """Get USD value of an asset"""
        if asset == 'USDT' or asset == 'BUSD':
            return amount
        
        try:
            if asset == 'BTC':
                ticker = self.client.get_symbol_ticker(symbol='BTCUSDT')
            elif asset == 'ETH':
                ticker = self.client.get_symbol_ticker(symbol='ETHUSDT')
            else:
                # Try to find a USDT pair
                ticker = self.client.get_symbol_ticker(symbol=f'{asset}USDT')
            
            return amount * float(ticker['price'])
        except:
            return 0

    def scan_opportunities(self):
        """Scan for arbitrage and trading opportunities"""
        try:
            opportunities = self.arbitrage_scanner.scan_all_pairs()
            
            for opp in opportunities:
                if opp['spread_percentage'] >= self.target_spread:
                    # Check if we have enough balance
                    if self.can_execute_trade(opp):
                        self.execute_arbitrage(opp)
                        
        except Exception as e:
            logging.error(f"Error scanning opportunities: {e}")

    def can_execute_trade(self, opportunity):
        """Check if we can execute a trade"""
        try:
            # Get USDT balance
            usdt_balance = self.get_asset_balance('USDT')
            
            # Calculate trade amount (between min and max)
            trade_amount = min(self.max_trade_amount, max(self.min_trade_amount, usdt_balance * 0.1))
            
            # Check if we have enough balance
            return usdt_balance >= trade_amount and trade_amount >= self.min_trade_amount
            
        except Exception as e:
            logging.error(f"Error checking trade feasibility: {e}")
            return False

    def get_asset_balance(self, asset):
        """Get balance for a specific asset"""
        try:
            balance = Balance.query.filter_by(asset=asset).first()
            return balance.free_balance if balance else 0
        except:
            return 0

    def execute_arbitrage(self, opportunity):
        """Execute an arbitrage trade"""
        try:
            symbol = opportunity['symbol']
            usdt_balance = self.get_asset_balance('USDT')
            
            # Calculate trade amount
            trade_amount = min(self.max_trade_amount, max(self.min_trade_amount, usdt_balance * 0.1))
            
            if trade_amount < self.min_trade_amount:
                return
            
            # Calculate quantity to buy
            buy_price = opportunity['buy_price']
            quantity = trade_amount / buy_price
            
            # Apply risk management
            if not self.risk_manager.can_execute_trade(symbol, trade_amount):
                return
            
            # Execute buy order
            buy_order = self.client.order_market_buy(
                symbol=symbol,
                quoteOrderQty=trade_amount
            )
            
            if buy_order['status'] == 'FILLED':
                # Record the trade
                trade = Trade(
                    symbol=symbol,
                    side='BUY',
                    quantity=float(buy_order['executedQty']),
                    price=float(buy_order['fills'][0]['price']),
                    total_value=trade_amount,
                    fee=sum(float(fill['commission']) for fill in buy_order['fills']),
                    strategy='arbitrage',
                    order_id=buy_order['orderId']
                )
                
                with db.session.begin():
                    db.session.add(trade)
                    db.session.commit()
                
                # Store position for potential sell
                self.positions[symbol] = {
                    'quantity': float(buy_order['executedQty']),
                    'buy_price': float(buy_order['fills'][0]['price']),
                    'timestamp': time.time()
                }
                
                logging.info(f"Executed arbitrage buy: {symbol} - {trade_amount} USDT")
                
                # Send notification
                if self.telegram_bot:
                    self.telegram_bot.send_message(f"🟢 Arbitrage Buy Executed\nSymbol: {symbol}\nAmount: ${trade_amount:.2f}\nPrice: {buy_price:.6f}")
                
                # Emit trade update
                socketio.emit('trade_executed', {
                    'symbol': symbol,
                    'side': 'BUY',
                    'amount': trade_amount,
                    'price': buy_price
                })
                
        except Exception as e:
            logging.error(f"API error executing arbitrage: {e}")
            self.create_alert("Trading Error", f"Failed to execute arbitrage: {str(e)}", "ERROR")
        except Exception as e:
            logging.error(f"Error executing arbitrage: {e}")

    def manage_positions(self):
        """Manage open positions and execute sells when profitable"""
        current_time = time.time()
        positions_to_remove = []
        
        for symbol, position in self.positions.items():
            try:
                # Get current price
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                buy_price = position['buy_price']
                quantity = position['quantity']
                
                # Calculate profit percentage
                profit_pct = (current_price - buy_price) / buy_price
                
                # Check stop loss
                if profit_pct <= -self.stop_loss_percentage:
                    self.execute_sell(symbol, position, current_price, "STOP_LOSS")
                    positions_to_remove.append(symbol)
                    continue
                
                # Check for profit target (0.8% minimum profit)
                if profit_pct >= 0.008:
                    self.execute_sell(symbol, position, current_price, "PROFIT_TARGET")
                    positions_to_remove.append(symbol)
                    continue
                
                # Time-based exit (hold for max 5 minutes)
                if current_time - position['timestamp'] > 300:  # 5 minutes
                    self.execute_sell(symbol, position, current_price, "TIME_EXIT")
                    positions_to_remove.append(symbol)
                    
            except Exception as e:
                logging.error(f"Error managing position {symbol}: {e}")
        
        # Remove closed positions
        for symbol in positions_to_remove:
            del self.positions[symbol]

    def execute_sell(self, symbol, position, current_price, reason):
        """Execute a sell order"""
        try:
            quantity = position['quantity']
            
            # Execute market sell
            sell_order = self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            
            if sell_order['status'] == 'FILLED':
                executed_price = float(sell_order['fills'][0]['price'])
                total_value = quantity * executed_price
                
                # Calculate profit/loss
                buy_total = quantity * position['buy_price']
                profit_loss = total_value - buy_total
                
                # Record the trade
                trade = Trade(
                    symbol=symbol,
                    side='SELL',
                    quantity=quantity,
                    price=executed_price,
                    total_value=total_value,
                    fee=sum(float(fill['commission']) for fill in sell_order['fills']),
                    strategy='arbitrage',
                    profit_loss=profit_loss,
                    order_id=sell_order['orderId']
                )
                
                with db.session.begin():
                    db.session.add(trade)
                    db.session.commit()
                
                logging.info(f"Executed sell: {symbol} - P/L: ${profit_loss:.2f} - Reason: {reason}")
                
                # Send notification
                if self.telegram_bot:
                    emoji = "🟢" if profit_loss > 0 else "🔴"
                    self.telegram_bot.send_message(f"{emoji} Position Closed\nSymbol: {symbol}\nProfit/Loss: ${profit_loss:.2f}\nReason: {reason}")
                
                # Emit trade update
                socketio.emit('trade_executed', {
                    'symbol': symbol,
                    'side': 'SELL',
                    'profit': profit_loss,
                    'reason': reason
                })
                
        except Exception as e:
            logging.error(f"Error executing sell for {symbol}: {e}")

    def update_daily_stats(self):
        """Update daily trading statistics"""
        try:
            today = datetime.now().date()
            
            # Get or create today's stats
            stats = DailyStats.query.filter_by(date=today).first()
            if not stats:
                # Get starting balance (end of yesterday or initial balance)
                yesterday = today - timedelta(days=1)
                yesterday_stats = DailyStats.query.filter_by(date=yesterday).first()
                starting_balance = yesterday_stats.ending_balance if yesterday_stats else 30.0  # Initial $30
                
                stats = DailyStats(
                    date=today,
                    starting_balance=starting_balance,
                    ending_balance=starting_balance
                )
                db.session.add(stats)
            
            # Update statistics
            today_trades = Trade.query.filter(
                Trade.executed_at >= datetime.combine(today, datetime.min.time())
            ).all()
            
            stats.total_trades = len(today_trades)
            stats.successful_trades = len([t for t in today_trades if t.profit_loss > 0])
            stats.total_profit = sum(t.profit_loss for t in today_trades)
            stats.total_fees = sum(t.fee for t in today_trades)
            
            # Get current total balance
            current_balance = sum(b.usd_value for b in Balance.query.all())
            stats.ending_balance = current_balance
            
            # Calculate ROI
            if stats.starting_balance > 0:
                stats.roi_percentage = ((stats.ending_balance - stats.starting_balance) / stats.starting_balance) * 100
            
            db.session.commit()
            
        except Exception as e:
            logging.error(f"Error updating daily stats: {e}")

    def create_alert(self, title, message, alert_type):
        """Create a system alert"""
        try:
            alert = Alert(
                title=title,
                message=message,
                alert_type=alert_type
            )
            
            with db.session.begin():
                db.session.add(alert)
                db.session.commit()
            
            # Emit alert via WebSocket
            socketio.emit('new_alert', {
                'title': title,
                'message': message,
                'type': alert_type
            })
            
        except Exception as e:
            logging.error(f"Error creating alert: {e}")

    def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        logging.info("Trading Engine stopped")
