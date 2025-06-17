import subprocess
import json
import logging
import time
from datetime import datetime

class CCXTIntegration:
    """Integración CCXT para múltiples exchanges"""
    
    def __init__(self):
        self.exchanges = ['binance', 'kucoin', 'okx', 'bybit', 'gate']
        logging.info("CCXT Integration initialized")
    
    def run_ccxt_command(self, command, exchange, symbol=None, params=None):
        """Ejecutar comando CCXT usando Node.js"""
        try:
            # Crear script temporal de Node.js
            script = f"""
const ccxt = require('ccxt');

async function execute() {{
    try {{
        const exchange = new ccxt.{exchange}({{
            sandbox: true,
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
            case 'fetch_markets':
                result = await exchange.fetchMarkets();
                break;
            case 'fetch_balance':
                result = await exchange.fetchBalance();
                break;
            case 'fetch_ohlcv':
                result = await exchange.fetchOHLCV('{symbol or "BTC/USDT"}', '1m', undefined, 10);
                break;
            default:
                throw new Error('Unknown command');
        }}
        
        console.log(JSON.stringify(result));
    }} catch (error) {{
        console.error(JSON.stringify({{error: error.message}}));
    }}
}}

execute();
"""
            
            # Escribir script temporal
            with open('/tmp/ccxt_script.js', 'w') as f:
                f.write(script)
            
            # Ejecutar con Node.js
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
    
    def get_ticker(self, exchange, symbol):
        """Obtener precio actual de un símbolo"""
        return self.run_ccxt_command('fetch_ticker', exchange, symbol)
    
    def get_order_book(self, exchange, symbol):
        """Obtener libro de órdenes"""
        return self.run_ccxt_command('fetch_order_book', exchange, symbol)
    
    def get_markets(self, exchange):
        """Obtener mercados disponibles"""
        return self.run_ccxt_command('fetch_markets', exchange)
    
    def scan_arbitrage_opportunities(self, symbol='BTC/USDT'):
        """Escanear oportunidades de arbitraje entre exchanges"""
        opportunities = []
        prices = {}
        
        # Obtener precios de todos los exchanges
        for exchange in self.exchanges:
            ticker = self.get_ticker(exchange, symbol)
            if ticker and 'bid' in ticker and 'ask' in ticker:
                prices[exchange] = {
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'last': ticker['last']
                }
        
        # Buscar oportunidades de arbitraje
        for buy_exchange, buy_data in prices.items():
            for sell_exchange, sell_data in prices.items():
                if buy_exchange != sell_exchange:
                    # Calcular spread
                    spread = (sell_data['bid'] - buy_data['ask']) / buy_data['ask']
                    
                    if spread > 0.003:  # Mínimo 0.3% de spread
                        opportunities.append({
                            'symbol': symbol,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'buy_price': buy_data['ask'],
                            'sell_price': sell_data['bid'],
                            'spread_percentage': spread * 100,
                            'potential_profit': 1000 * spread  # Ganancia en $1000
                        })
        
        # Ordenar por mayor spread
        opportunities.sort(key=lambda x: x['spread_percentage'], reverse=True)
        return opportunities[:5]  # Top 5 oportunidades
    
    def get_multi_exchange_prices(self, symbols=['BTC/USDT', 'ETH/USDT', 'ADA/USDT']):
        """Obtener precios de múltiples exchanges para comparación"""
        results = {}
        
        for symbol in symbols:
            results[symbol] = {}
            for exchange in self.exchanges:
                ticker = self.get_ticker(exchange, symbol)
                if ticker:
                    results[symbol][exchange] = {
                        'price': ticker.get('last', 0),
                        'bid': ticker.get('bid', 0),
                        'ask': ticker.get('ask', 0),
                        'volume': ticker.get('baseVolume', 0)
                    }
        
        return results
    
    def find_best_prices(self, symbol='BTC/USDT'):
        """Encontrar mejores precios de compra y venta"""
        best_buy = {'exchange': None, 'price': float('inf')}
        best_sell = {'exchange': None, 'price': 0}
        
        for exchange in self.exchanges:
            ticker = self.get_ticker(exchange, symbol)
            if ticker and 'ask' in ticker and 'bid' in ticker:
                # Mejor precio de compra (ask más bajo)
                if ticker['ask'] < best_buy['price']:
                    best_buy = {
                        'exchange': exchange,
                        'price': ticker['ask']
                    }
                
                # Mejor precio de venta (bid más alto)
                if ticker['bid'] > best_sell['price']:
                    best_sell = {
                        'exchange': exchange,
                        'price': ticker['bid']
                    }
        
        return {
            'symbol': symbol,
            'best_buy': best_buy,
            'best_sell': best_sell,
            'spread': best_sell['price'] - best_buy['price'],
            'spread_percentage': ((best_sell['price'] - best_buy['price']) / best_buy['price']) * 100
        }