import logging
from binance.exceptions import BinanceAPIException
import time
from collections import defaultdict

class ArbitrageScanner:
    def __init__(self, client):
        self.client = client
        self.price_cache = {}
        self.cache_duration = 2  # Cache prices for 2 seconds
        
        # Focus on altcoins with typically higher spreads
        self.target_symbols = [
            'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'XLMUSDT',
            'VETUSDT', 'TRXUSDT', 'EOSUSDT', 'XRPUSDT', 'ALGOUSDT',
            'ATOMUSDT', 'AVAXUSDT', 'MATICUSDT', 'SOLUSDT', 'LUNAUSDT',
            'NEARUSDT', 'FTMUSDT', 'ONEUSDT', 'HBARUSDT', 'ICPUSDT'
        ]
        
        logging.info("Arbitrage Scanner initialized")

    def get_order_book(self, symbol):
        """Get order book for a symbol with caching"""
        cache_key = f"{symbol}_orderbook"
        current_time = time.time()
        
        # Check cache
        if cache_key in self.price_cache:
            cached_data, timestamp = self.price_cache[cache_key]
            if current_time - timestamp < self.cache_duration:
                return cached_data
        
        try:
            # Get order book depth
            orderbook = self.client.get_order_book(symbol=symbol, limit=5)
            
            # Cache the result
            self.price_cache[cache_key] = (orderbook, current_time)
            
            return orderbook
            
        except BinanceAPIException as e:
            logging.error(f"Error getting order book for {symbol}: {e}")
            return None

    def calculate_spread(self, symbol):
        """Calculate bid-ask spread for a symbol"""
        try:
            orderbook = self.get_order_book(symbol)
            if not orderbook:
                return None
            
            best_bid = float(orderbook['bids'][0][0])  # Highest buy price
            best_ask = float(orderbook['asks'][0][0])  # Lowest sell price
            
            # Calculate spread percentage
            spread_pct = (best_ask - best_bid) / best_bid
            
            # Get volumes
            bid_volume = float(orderbook['bids'][0][1])
            ask_volume = float(orderbook['asks'][0][1])
            
            return {
                'symbol': symbol,
                'bid_price': best_bid,
                'ask_price': best_ask,
                'spread_percentage': spread_pct,
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'min_volume': min(bid_volume, ask_volume)
            }
            
        except Exception as e:
            logging.error(f"Error calculating spread for {symbol}: {e}")
            return None

    def scan_all_pairs(self):
        """Scan all target pairs for arbitrage opportunities"""
        opportunities = []
        
        for symbol in self.target_symbols:
            try:
                spread_data = self.calculate_spread(symbol)
                
                if spread_data and spread_data['spread_percentage'] > 0.005:  # > 0.5%
                    # Calculate potential profit for a $10 trade
                    trade_amount = 10.0
                    potential_profit = trade_amount * spread_data['spread_percentage']
                    
                    # Only consider if minimum volume is sufficient
                    if spread_data['min_volume'] * spread_data['bid_price'] >= trade_amount:
                        opportunity = {
                            'symbol': symbol,
                            'buy_price': spread_data['bid_price'],
                            'sell_price': spread_data['ask_price'],
                            'spread_percentage': spread_data['spread_percentage'],
                            'volume': spread_data['min_volume'],
                            'potential_profit': potential_profit,
                            'trade_amount': trade_amount
                        }
                        
                        opportunities.append(opportunity)
                        
            except Exception as e:
                logging.error(f"Error scanning {symbol}: {e}")
                continue
        
        # Sort by spread percentage (highest first)
        opportunities.sort(key=lambda x: x['spread_percentage'], reverse=True)
        
        return opportunities[:5]  # Return top 5 opportunities

    def scan_micro_movements(self):
        """Scan for micro price movements suitable for scalping"""
        opportunities = []
        
        for symbol in self.target_symbols:
            try:
                # Get recent price data
                klines = self.client.get_historical_klines(
                    symbol, '1m', '5 minutes ago UTC'
                )
                
                if len(klines) < 3:
                    continue
                
                # Analyze recent price movements
                prices = [float(kline[4]) for kline in klines]  # Close prices
                
                # Calculate price volatility
                price_changes = []
                for i in range(1, len(prices)):
                    change = (prices[i] - prices[i-1]) / prices[i-1]
                    price_changes.append(abs(change))
                
                avg_volatility = sum(price_changes) / len(price_changes)
                
                # Look for high volatility (good for scalping)
                if avg_volatility > 0.003:  # > 0.3% average movement
                    current_price = prices[-1]
                    
                    opportunity = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'volatility': avg_volatility,
                        'strategy': 'scalping',
                        'signal': self.get_scalping_signal(prices)
                    }
                    
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logging.error(f"Error scanning micro movements for {symbol}: {e}")
                continue
        
        return opportunities

    def get_scalping_signal(self, prices):
        """Generate a simple scalping signal based on price trend"""
        if len(prices) < 3:
            return 'HOLD'
        
        # Simple momentum strategy
        recent_prices = prices[-3:]
        
        # If price is consistently rising
        if recent_prices[0] < recent_prices[1] < recent_prices[2]:
            return 'BUY'
        
        # If price is consistently falling
        if recent_prices[0] > recent_prices[1] > recent_prices[2]:
            return 'SELL'
        
        return 'HOLD'

    def detect_volume_spikes(self):
        """Detect volume spikes that might indicate pump/dump opportunities"""
        opportunities = []
        
        for symbol in self.target_symbols:
            try:
                # Get 24hr ticker data
                ticker = self.client.get_24hr_ticker(symbol=symbol)
                
                current_volume = float(ticker['volume'])
                price_change_pct = float(ticker['priceChangePercent'])
                
                # Look for high volume with significant price movement
                if current_volume > 1000000 and abs(price_change_pct) > 5:  # > 5% price change
                    opportunity = {
                        'symbol': symbol,
                        'volume': current_volume,
                        'price_change_pct': price_change_pct,
                        'current_price': float(ticker['lastPrice']),
                        'strategy': 'volume_spike',
                        'signal': 'BUY' if price_change_pct > 0 else 'SELL'
                    }
                    
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logging.error(f"Error detecting volume spikes for {symbol}: {e}")
                continue
        
        return opportunities

    def get_grid_trading_levels(self, symbol, num_levels=5):
        """Calculate grid trading levels for a symbol"""
        try:
            # Get recent price data
            klines = self.client.get_historical_klines(
                symbol, '1h', '24 hours ago UTC'
            )
            
            if len(klines) < 10:
                return None
            
            # Calculate support and resistance levels
            highs = [float(kline[2]) for kline in klines]  # High prices
            lows = [float(kline[3]) for kline in klines]   # Low prices
            
            highest = max(highs)
            lowest = min(lows)
            current_price = float(klines[-1][4])  # Last close price
            
            # Create grid levels
            price_range = highest - lowest
            grid_spacing = price_range / (num_levels + 1)
            
            buy_levels = []
            sell_levels = []
            
            for i in range(1, num_levels + 1):
                buy_level = lowest + (i * grid_spacing)
                sell_level = buy_level + (grid_spacing * 0.5)  # 50% of grid spacing as profit target
                
                if buy_level < current_price:
                    buy_levels.append(buy_level)
                if sell_level > current_price:
                    sell_levels.append(sell_level)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'buy_levels': buy_levels,
                'sell_levels': sell_levels,
                'grid_spacing': grid_spacing,
                'support': lowest,
                'resistance': highest
            }
            
        except Exception as e:
            logging.error(f"Error calculating grid levels for {symbol}: {e}")
            return None
