import random
import time
import logging
from datetime import datetime

class ExchangeSimulator:
    """Simulates exchange behavior for testing without real API calls"""
    
    def __init__(self, name="Simulator"):
        self.name = name
        self.base_prices = {
            'BTCUSDT': 43500.0,
            'ETHUSDT': 2650.0,
            'ADAUSDT': 0.485,
            'DOTUSDT': 7.32,
            'LINKUSDT': 14.85,
            'LTCUSDT': 72.50,
            'XLMUSDT': 0.125,
            'VETUSDT': 0.0285,
            'TRXUSDT': 0.095,
            'EOSUSDT': 0.875,
            'XRPUSDT': 0.545,
            'ALGOUSDT': 0.165,
            'ATOMUSDT': 9.85,
            'AVAXUSDT': 38.50,
            'MATICUSDT': 0.825,
            'SOLUSDT': 98.50,
            'NEARUSDT': 3.45,
            'FTMUSDT': 0.385,
            'ONEUSDT': 0.0145,
            'HBARUSDT': 0.075,
            'ICPUSDT': 12.85
        }
        
        # Simulate account balances
        self.balances = {
            'USDT': {'free': 30.0, 'locked': 0.0},
            'BTC': {'free': 0.0, 'locked': 0.0},
            'ETH': {'free': 0.0, 'locked': 0.0}
        }
        
        logging.info(f"{self.name} exchange simulator initialized")

    def get_symbol_ticker(self, symbol):
        """Simulate ticker price with small random fluctuations"""
        if symbol not in self.base_prices:
            return None
        
        base_price = self.base_prices[symbol]
        # Add random fluctuation of ±0.1%
        fluctuation = random.uniform(-0.001, 0.001)
        current_price = base_price * (1 + fluctuation)
        
        return {'price': str(current_price)}

    def get_order_book(self, symbol, limit=100):
        """Simulate order book with realistic bid/ask spreads"""
        if symbol not in self.base_prices:
            return None
        
        base_price = self.base_prices[symbol]
        # Create realistic spread (0.05% to 0.3%)
        spread_pct = random.uniform(0.0005, 0.003)
        spread = base_price * spread_pct
        
        bid_price = base_price - (spread / 2)
        ask_price = base_price + (spread / 2)
        
        # Generate multiple price levels
        bids = []
        asks = []
        
        for i in range(5):
            bid_level = bid_price - (i * spread * 0.1)
            ask_level = ask_price + (i * spread * 0.1)
            
            # Random volumes between 0.1 and 10
            bid_volume = random.uniform(0.1, 10.0)
            ask_volume = random.uniform(0.1, 10.0)
            
            bids.append([str(bid_level), str(bid_volume)])
            asks.append([str(ask_level), str(ask_volume)])
        
        return {
            'bids': bids,
            'asks': asks
        }

    def get_account(self):
        """Simulate account information"""
        balances = []
        for asset, balance in self.balances.items():
            balances.append({
                'asset': asset,
                'free': str(balance['free']),
                'locked': str(balance['locked'])
            })
        
        return {'balances': balances}

    def order_market_buy(self, symbol, quoteOrderQty):
        """Simulate market buy order execution"""
        try:
            # Check if we have enough USDT
            if self.balances['USDT']['free'] < float(quoteOrderQty):
                return None
            
            # Get current price
            ticker = self.get_symbol_ticker(symbol)
            if not ticker:
                return None
            
            price = float(ticker['price'])
            # Add some slippage (0.01% to 0.05%)
            slippage = random.uniform(0.0001, 0.0005)
            executed_price = price * (1 + slippage)
            
            # Calculate quantity bought
            quantity = float(quoteOrderQty) / executed_price
            fee = float(quoteOrderQty) * 0.001  # 0.1% fee
            
            # Update balances
            self.balances['USDT']['free'] -= float(quoteOrderQty)
            
            # Extract base asset from symbol (e.g., BTC from BTCUSDT)
            base_asset = symbol.replace('USDT', '')
            if base_asset not in self.balances:
                self.balances[base_asset] = {'free': 0.0, 'locked': 0.0}
            
            self.balances[base_asset]['free'] += quantity
            
            return {
                'status': 'FILLED',
                'executedQty': str(quantity),
                'orderId': str(int(time.time() * 1000)),
                'fills': [{
                    'price': str(executed_price),
                    'commission': str(fee),
                    'commissionAsset': 'USDT'
                }]
            }
            
        except Exception as e:
            logging.error(f"Error simulating buy order: {e}")
            return None

    def order_market_sell(self, symbol, quantity):
        """Simulate market sell order execution"""
        try:
            base_asset = symbol.replace('USDT', '')
            
            # Check if we have enough of the asset
            if base_asset not in self.balances or self.balances[base_asset]['free'] < float(quantity):
                return None
            
            # Get current price
            ticker = self.get_symbol_ticker(symbol)
            if not ticker:
                return None
            
            price = float(ticker['price'])
            # Add some slippage (negative for sells)
            slippage = random.uniform(0.0001, 0.0005)
            executed_price = price * (1 - slippage)
            
            # Calculate USDT received
            usdt_received = float(quantity) * executed_price
            fee = usdt_received * 0.001  # 0.1% fee
            net_usdt = usdt_received - fee
            
            # Update balances
            self.balances[base_asset]['free'] -= float(quantity)
            self.balances['USDT']['free'] += net_usdt
            
            return {
                'status': 'FILLED',
                'executedQty': quantity,
                'orderId': str(int(time.time() * 1000)),
                'fills': [{
                    'price': str(executed_price),
                    'commission': str(fee),
                    'commissionAsset': 'USDT'
                }]
            }
            
        except Exception as e:
            logging.error(f"Error simulating sell order: {e}")
            return None

    def get_24hr_ticker(self, symbol=None):
        """Simulate 24hr ticker statistics"""
        if symbol:
            if symbol not in self.base_prices:
                return None
            
            base_price = self.base_prices[symbol]
            change_pct = random.uniform(-5.0, 5.0)  # ±5% daily change
            volume = random.uniform(1000000, 10000000)  # Random volume
            
            return {
                'symbol': symbol,
                'priceChangePercent': str(change_pct),
                'volume': str(volume),
                'lastPrice': str(base_price)
            }
        else:
            # Return all symbols
            tickers = []
            for symbol, base_price in self.base_prices.items():
                change_pct = random.uniform(-5.0, 5.0)
                volume = random.uniform(1000000, 10000000)
                
                tickers.append({
                    'symbol': symbol,
                    'priceChangePercent': str(change_pct),
                    'volume': str(volume),
                    'lastPrice': str(base_price)
                })
            
            return tickers

    def get_historical_klines(self, symbol, interval, start_str, end_str=None, limit=500):
        """Simulate historical klines data"""
        if symbol not in self.base_prices:
            return []
        
        base_price = self.base_prices[symbol]
        klines = []
        
        # Generate 5 klines for recent data
        current_time = int(time.time() * 1000)
        for i in range(5):
            timestamp = current_time - (i * 60000)  # 1 minute intervals
            
            # Generate OHLCV data with small variations
            open_price = base_price * (1 + random.uniform(-0.002, 0.002))
            high_price = open_price * (1 + random.uniform(0, 0.005))
            low_price = open_price * (1 - random.uniform(0, 0.005))
            close_price = open_price * (1 + random.uniform(-0.002, 0.002))
            volume = random.uniform(100, 1000)
            
            kline = [
                timestamp,                    # Open time
                str(open_price),             # Open
                str(high_price),             # High
                str(low_price),              # Low
                str(close_price),            # Close
                str(volume),                 # Volume
                timestamp + 59999,           # Close time
                "0",                         # Quote asset volume
                0,                           # Number of trades
                "0",                         # Taker buy base asset volume
                "0",                         # Taker buy quote asset volume
                "0"                          # Ignore
            ]
            klines.append(kline)
        
        return klines

    def test_connection(self):
        """Simulate successful connection test"""
        return True