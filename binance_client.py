import time
import hashlib
import hmac
import requests
import json
import logging
from urllib.parse import urlencode

class BinanceClient:
    def __init__(self, api_key, api_secret, testnet=False):
        self.api_key = api_key
        self.api_secret = api_secret
        
        if testnet:
            self.base_url = 'https://testnet.binance.vision'
        else:
            self.base_url = 'https://api.binance.com'
        
        self.session = requests.Session()
        logging.info("Binance client initialized")

    def _generate_signature(self, query_string):
        """Generate signature for Binance API"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, endpoint, method='GET', params=None, signed=False):
        """Make request to Binance API"""
        url = self.base_url + endpoint
        
        if params is None:
            params = {}
        
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._generate_signature(query_string)
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Binance API request failed: {e}")
            return None

    def get_account(self):
        """Get account information"""
        return self._make_request('/api/v3/account', signed=True)

    def get_symbol_ticker(self, symbol):
        """Get ticker price for a symbol"""
        params = {'symbol': symbol}
        return self._make_request('/api/v3/ticker/price', params=params)

    def get_order_book(self, symbol, limit=100):
        """Get order book for a symbol"""
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request('/api/v3/depth', params=params)

    def get_24hr_ticker(self, symbol=None):
        """Get 24hr ticker statistics"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request('/api/v3/ticker/24hr', params=params)

    def get_historical_klines(self, symbol, interval, start_str, end_str=None, limit=500):
        """Get historical klines/candlesticks"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(time.time() * 1000) - 300000,  # 5 minutes ago
            'limit': limit
        }
        return self._make_request('/api/v3/klines', params=params)

    def order_market_buy(self, symbol, quoteOrderQty):
        """Place market buy order"""
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': quoteOrderQty
        }
        return self._make_request('/api/v3/order', method='POST', params=params, signed=True)

    def order_market_sell(self, symbol, quantity):
        """Place market sell order"""
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': quantity
        }
        return self._make_request('/api/v3/order', method='POST', params=params, signed=True)

    def test_connection(self):
        """Test API connection"""
        try:
            result = self._make_request('/api/v3/time')
            return result is not None
        except Exception as e:
            logging.error(f"Binance connection test failed: {e}")
            return False

    def get_exchange_info(self):
        """Get exchange information"""
        return self._make_request('/api/v3/exchangeInfo')