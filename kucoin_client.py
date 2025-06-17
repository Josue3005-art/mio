import time
import hashlib
import hmac
import base64
import requests
import json
import logging
from datetime import datetime

class KuCoinClient:
    def __init__(self, api_key, api_secret, passphrase, sandbox=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        
        if sandbox:
            self.base_url = 'https://openapi-sandbox.kucoin.com'
        else:
            self.base_url = 'https://api.kucoin.com'
        
        self.session = requests.Session()
        logging.info("KuCoin client initialized")

    def _generate_signature(self, timestamp, method, endpoint, body=''):
        """Generate signature for KuCoin API"""
        str_to_sign = str(timestamp) + method + endpoint + body
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                str_to_sign.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        passphrase_signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                self.passphrase.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return signature, passphrase_signature

    def _make_request(self, method, endpoint, params=None, body=None):
        """Make authenticated request to KuCoin API"""
        timestamp = int(time.time() * 1000)
        
        if body:
            body_str = json.dumps(body)
        else:
            body_str = ''
        
        signature, passphrase_signature = self._generate_signature(
            timestamp, method.upper(), endpoint, body_str
        )
        
        headers = {
            'KC-API-KEY': self.api_key,
            'KC-API-SIGN': signature,
            'KC-API-TIMESTAMP': str(timestamp),
            'KC-API-PASSPHRASE': passphrase_signature,
            'KC-API-KEY-VERSION': '2',
            'Content-Type': 'application/json'
        }
        
        url = self.base_url + endpoint
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=body)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"KuCoin API request failed: {e}")
            return None

    def get_account_balance(self):
        """Get account balance"""
        endpoint = '/api/v1/accounts'
        return self._make_request('GET', endpoint)

    def get_symbol_ticker(self, symbol):
        """Get ticker for a specific symbol"""
        endpoint = f'/api/v1/market/orderbook/level1'
        params = {'symbol': symbol}
        return self._make_request('GET', endpoint, params=params)

    def get_order_book(self, symbol, limit=20):
        """Get order book for a symbol"""
        endpoint = f'/api/v1/market/orderbook/level2_{limit}'
        params = {'symbol': symbol}
        return self._make_request('GET', endpoint, params=params)

    def get_24hr_ticker(self, symbol=None):
        """Get 24hr ticker statistics"""
        if symbol:
            endpoint = f'/api/v1/market/stats'
            params = {'symbol': symbol}
        else:
            endpoint = f'/api/v1/market/allTickers'
            params = None
        
        return self._make_request('GET', endpoint, params=params)

    def place_market_buy_order(self, symbol, quote_quantity):
        """Place market buy order"""
        endpoint = '/api/v1/orders'
        body = {
            'clientOid': str(int(time.time() * 1000)),
            'side': 'buy',
            'symbol': symbol,
            'type': 'market',
            'quoteSize': str(quote_quantity)
        }
        return self._make_request('POST', endpoint, body=body)

    def place_market_sell_order(self, symbol, quantity):
        """Place market sell order"""
        endpoint = '/api/v1/orders'
        body = {
            'clientOid': str(int(time.time() * 1000)),
            'side': 'sell',
            'symbol': symbol,
            'type': 'market',
            'size': str(quantity)
        }
        return self._make_request('POST', endpoint, body=body)

    def get_symbols(self):
        """Get all available trading symbols"""
        endpoint = '/api/v1/symbols'
        return self._make_request('GET', endpoint)

    def test_connection(self):
        """Test API connection"""
        try:
            endpoint = '/api/v1/timestamp'
            result = self._make_request('GET', endpoint)
            return result is not None
        except Exception as e:
            logging.error(f"KuCoin connection test failed: {e}")
            return False