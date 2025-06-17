import logging
from datetime import datetime, timedelta
from collections import defaultdict
import time

class RiskManager:
    def __init__(self):
        self.max_trades_per_hour = 10
        self.max_daily_loss = 5.0  # Max $5 loss per day
        self.max_position_size = 15.0  # Max $15 per position
        self.max_open_positions = 3
        
        # Track trading activity
        self.trade_history = defaultdict(list)
        self.daily_losses = defaultdict(float)
        self.position_sizes = {}
        
        logging.info("Risk Manager initialized")

    def can_execute_trade(self, symbol, amount):
        """Check if a trade can be executed based on risk parameters"""
        try:
            current_time = time.time()
            current_date = datetime.now().date()
            
            # Check position size limit
            if amount > self.max_position_size:
                logging.warning(f"Trade amount ${amount} exceeds max position size ${self.max_position_size}")
                return False
            
            # Check hourly trade limit
            hour_ago = current_time - 3600
            recent_trades = [t for t in self.trade_history[symbol] if t > hour_ago]
            
            if len(recent_trades) >= self.max_trades_per_hour:
                logging.warning(f"Hourly trade limit reached for {symbol}")
                return False
            
            # Check daily loss limit
            if self.daily_losses[current_date] >= self.max_daily_loss:
                logging.warning(f"Daily loss limit reached: ${self.daily_losses[current_date]}")
                return False
            
            # Check maximum open positions
            if len(self.position_sizes) >= self.max_open_positions:
                logging.warning(f"Maximum open positions reached: {len(self.position_sizes)}")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error in risk check: {e}")
            return False

    def record_trade(self, symbol, amount, profit_loss=None):
        """Record a trade for risk tracking"""
        try:
            current_time = time.time()
            current_date = datetime.now().date()
            
            # Record trade timestamp
            self.trade_history[symbol].append(current_time)
            
            # Clean old trade records (keep last 24 hours)
            day_ago = current_time - 86400
            self.trade_history[symbol] = [t for t in self.trade_history[symbol] if t > day_ago]
            
            # Record position
            if profit_loss is None:  # Opening position
                self.position_sizes[symbol] = amount
            else:  # Closing position
                if symbol in self.position_sizes:
                    del self.position_sizes[symbol]
                
                # Track losses
                if profit_loss < 0:
                    self.daily_losses[current_date] += abs(profit_loss)
            
            # Clean old daily loss records
            week_ago = current_date - timedelta(days=7)
            self.daily_losses = {date: loss for date, loss in self.daily_losses.items() if date > week_ago}
            
        except Exception as e:
            logging.error(f"Error recording trade: {e}")

    def get_position_size(self, balance, volatility):
        """Calculate appropriate position size based on balance and volatility"""
        try:
            # Base position size as percentage of balance
            base_percentage = 0.1  # 10% of balance
            
            # Adjust based on volatility
            if volatility > 0.05:  # High volatility (>5%)
                volatility_multiplier = 0.5
            elif volatility > 0.02:  # Medium volatility (2-5%)
                volatility_multiplier = 0.75
            else:  # Low volatility (<2%)
                volatility_multiplier = 1.0
            
            position_size = balance * base_percentage * volatility_multiplier
            
            # Apply limits
            position_size = max(5.0, min(position_size, self.max_position_size))
            
            return position_size
            
        except Exception as e:
            logging.error(f"Error calculating position size: {e}")
            return 5.0  # Default minimum

    def check_stop_loss(self, entry_price, current_price, side):
        """Check if stop loss should be triggered"""
        try:
            if side == 'BUY':
                # For long positions, stop loss when price drops
                loss_percentage = (entry_price - current_price) / entry_price
            else:
                # For short positions, stop loss when price rises
                loss_percentage = (current_price - entry_price) / entry_price
            
            return loss_percentage >= 0.02  # 2% stop loss
            
        except Exception as e:
            logging.error(f"Error checking stop loss: {e}")
            return False

    def check_take_profit(self, entry_price, current_price, side, target_profit=0.008):
        """Check if take profit should be triggered"""
        try:
            if side == 'BUY':
                # For long positions, take profit when price rises
                profit_percentage = (current_price - entry_price) / entry_price
            else:
                # For short positions, take profit when price drops
                profit_percentage = (entry_price - current_price) / entry_price
            
            return profit_percentage >= target_profit  # 0.8% default profit target
            
        except Exception as e:
            logging.error(f"Error checking take profit: {e}")
            return False

    def get_risk_metrics(self):
        """Get current risk metrics"""
        try:
            current_date = datetime.now().date()
            current_time = time.time()
            hour_ago = current_time - 3600
            
            # Count recent trades
            total_recent_trades = sum(
                len([t for t in trades if t > hour_ago]) 
                for trades in self.trade_history.values()
            )
            
            return {
                'open_positions': len(self.position_sizes),
                'max_open_positions': self.max_open_positions,
                'recent_trades_1h': total_recent_trades,
                'max_trades_per_hour': self.max_trades_per_hour,
                'daily_loss': self.daily_losses.get(current_date, 0),
                'max_daily_loss': self.max_daily_loss,
                'position_utilization': len(self.position_sizes) / self.max_open_positions * 100
            }
            
        except Exception as e:
            logging.error(f"Error getting risk metrics: {e}")
            return {}

    def should_reduce_exposure(self):
        """Check if exposure should be reduced due to accumulated losses"""
        try:
            current_date = datetime.now().date()
            daily_loss = self.daily_losses.get(current_date, 0)
            
            # Reduce exposure if daily loss exceeds 50% of limit
            return daily_loss >= (self.max_daily_loss * 0.5)
            
        except Exception as e:
            logging.error(f"Error checking exposure reduction: {e}")
            return False

    def calculate_kelly_criterion(self, win_rate, avg_win, avg_loss):
        """Calculate Kelly Criterion for optimal position sizing"""
        try:
            if avg_loss == 0 or win_rate == 0:
                return 0.1  # Default 10%
            
            # Kelly formula: f = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b
            
            # Apply conservative factor (use 25% of Kelly)
            conservative_kelly = kelly_fraction * 0.25
            
            # Ensure it's within reasonable bounds
            return max(0.05, min(conservative_kelly, 0.2))  # Between 5% and 20%
            
        except Exception as e:
            logging.error(f"Error calculating Kelly criterion: {e}")
            return 0.1
