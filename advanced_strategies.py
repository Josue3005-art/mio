import time
import statistics
from datetime import datetime, timedelta
from app import app, db
from models import Trade, Alert, TradingConfig
from ccxt_integration import CCXTIntegration
import logging

logger = logging.getLogger(__name__)

class AdvancedTradingStrategies:
    """Estrategias avanzadas de trading: Grid, Scalping, Pump/Dump Detection"""
    
    def __init__(self):
        self.ccxt = CCXTIntegration()
        self.exchanges = ['gateio', 'mexc', 'okx', 'bitget']
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOGE/USDT', 'XRP/USDT']
        
    def get_config(self, key, default=None):
        """Obtener configuración desde base de datos"""
        with app.app_context():
            config = TradingConfig.query.filter_by(key=key).first()
            return config.value if config else default
    
    def grid_trading_strategy(self, symbol='BTC/USDT', grid_levels=5):
        """
        Estrategia Grid Trading - coloca órdenes de compra/venta en niveles específicos
        """
        logger.info(f"Ejecutando Grid Trading para {symbol}")
        
        try:
            # Obtener precio actual desde múltiples exchanges
            prices = []
            for exchange in self.exchanges:
                try:
                    ticker = self.ccxt.get_ticker(exchange, symbol)
                    if ticker and 'last' in ticker:
                        prices.append(float(ticker['last']))
                except Exception as e:
                    logger.warning(f"Error obteniendo precio de {exchange}: {e}")
                    continue
            
            if not prices:
                return None
                
            current_price = statistics.median(prices)
            
            # Calcular niveles de grid (±2% del precio actual)
            grid_range_config = self.get_config('grid_range_percent', '2.0')
            grid_range = float(grid_range_config) / 100 if grid_range_config else 0.02
            grid_spacing = (current_price * grid_range * 2) / grid_levels
            
            levels = []
            for i in range(grid_levels):
                level_price = current_price - (grid_range * current_price) + (i * grid_spacing)
                levels.append({
                    'price': level_price,
                    'side': 'BUY' if level_price < current_price else 'SELL',
                    'distance': abs(level_price - current_price) / current_price * 100
                })
            
            # Buscar oportunidades en los niveles de grid
            opportunities = []
            for level in levels:
                if level['distance'] <= 0.5:  # Dentro del 0.5% del precio actual
                    opportunities.append({
                        'symbol': symbol,
                        'strategy': 'grid_trading',
                        'price': level['price'],
                        'side': level['side'],
                        'potential_profit': grid_spacing / current_price * 100
                    })
            
            if opportunities:
                self.create_alert(
                    "Grid Trading Opportunity",
                    f"Found {len(opportunities)} grid levels for {symbol} at ${current_price:.4f}",
                    "INFO"
                )
                
            return opportunities
            
        except Exception as e:
            logger.error(f"Error en Grid Trading: {e}")
            return None
    
    def scalping_strategy(self, symbol='BTC/USDT', timeframe='1m'):
        """
        Estrategia de Scalping - detecta micro-movimientos para trades rápidos
        """
        logger.info(f"Ejecutando Scalping para {symbol}")
        
        try:
            price_history = []
            
            # Recopilar datos de precio de múltiples exchanges
            for exchange in self.exchanges:
                try:
                    ticker = self.ccxt.get_ticker(exchange, symbol)
                    if ticker and 'last' in ticker:
                        price_history.append({
                            'exchange': exchange,
                            'price': float(ticker['last']),
                            'volume': float(ticker.get('baseVolume', 0)),
                            'timestamp': time.time()
                        })
                except Exception as e:
                    continue
            
            if len(price_history) < 2:
                return None
            
            # Analizar volatilidad y momentum
            prices = [p['price'] for p in price_history]
            volumes = [p['volume'] for p in price_history]
            
            price_std = statistics.stdev(prices) if len(prices) > 1 else 0
            avg_price = statistics.mean(prices)
            avg_volume = statistics.mean(volumes) if volumes else 0
            
            # Detectar condiciones de scalping
            volatility_config = self.get_config('scalping_volatility', '0.1')
            volume_config = self.get_config('scalping_volume', '100')
            volatility_threshold = float(volatility_config) / 100 if volatility_config else 0.001
            volume_threshold = float(volume_config) if volume_config else 100
            
            if price_std / avg_price > volatility_threshold and avg_volume > volume_threshold:
                # Identificar exchange con mejor precio
                best_buy = min(price_history, key=lambda x: x['price'])
                best_sell = max(price_history, key=lambda x: x['price'])
                
                spread = (best_sell['price'] - best_buy['price']) / best_buy['price'] * 100
                
                if spread > 0.05:  # Mínimo 0.05% de spread
                    opportunity = {
                        'symbol': symbol,
                        'strategy': 'scalping',
                        'buy_exchange': best_buy['exchange'],
                        'sell_exchange': best_sell['exchange'],
                        'buy_price': best_buy['price'],
                        'sell_price': best_sell['price'],
                        'spread': spread,
                        'volatility': price_std / avg_price * 100
                    }
                    
                    self.create_alert(
                        "Scalping Opportunity",
                        f"Scalping detected for {symbol}: {spread:.3f}% spread",
                        "SUCCESS"
                    )
                    
                    return opportunity
            
            return None
            
        except Exception as e:
            logger.error(f"Error en Scalping: {e}")
            return None
    
    def pump_dump_detector(self, lookback_minutes=5):
        """
        Detector de Pump & Dump - identifica movimientos de precio anómalos
        """
        logger.info("Ejecutando detector de Pump & Dump")
        
        try:
            alerts = []
            
            for symbol in self.symbols:
                price_data = []
                volume_data = []
                
                # Recopilar datos de múltiples exchanges
                for exchange in self.exchanges:
                    try:
                        ticker = self.ccxt.get_ticker(exchange, symbol)
                        if ticker:
                            price_data.append(float(ticker['last']))
                            volume_data.append(float(ticker.get('baseVolume', 0)))
                    except Exception:
                        continue
                
                if len(price_data) < 2:
                    continue
                
                avg_price = statistics.mean(price_data)
                avg_volume = statistics.mean(volume_data)
                price_std = statistics.stdev(price_data) if len(price_data) > 1 else 0
                
                # Criterios para detectar pump/dump
                pump_threshold = float(self.get_config('pump_threshold', '3.0')) / 100  # 3%
                dump_threshold = float(self.get_config('dump_threshold', '-2.0')) / 100  # -2%
                volume_spike = float(self.get_config('volume_spike', '150')) / 100  # 150%
                
                price_change = (max(price_data) - min(price_data)) / min(price_data)
                
                # Detectar PUMP
                if price_change > pump_threshold:
                    alerts.append({
                        'type': 'PUMP',
                        'symbol': symbol,
                        'price_change': price_change * 100,
                        'avg_volume': avg_volume,
                        'volatility': price_std / avg_price * 100,
                        'confidence': min(price_change / pump_threshold, 2.0)
                    })
                
                # Detectar DUMP
                elif price_change < dump_threshold:
                    alerts.append({
                        'type': 'DUMP',
                        'symbol': symbol,
                        'price_change': price_change * 100,
                        'avg_volume': avg_volume,
                        'volatility': price_std / avg_price * 100,
                        'confidence': min(abs(price_change) / abs(dump_threshold), 2.0)
                    })
            
            # Crear alertas para movimientos significativos
            for alert in alerts:
                self.create_alert(
                    f"{alert['type']} Detected",
                    f"{alert['symbol']}: {alert['price_change']:.2f}% movement detected "
                    f"(Confidence: {alert['confidence']:.1f})",
                    "WARNING" if alert['type'] == 'DUMP' else "INFO"
                )
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error en Pump/Dump detector: {e}")
            return []
    
    def momentum_strategy(self, symbol='BTC/USDT'):
        """
        Estrategia de Momentum - sigue tendencias de precios
        """
        try:
            # Obtener datos de precio históricos simulados
            price_points = []
            
            for exchange in self.exchanges:
                try:
                    ticker = self.ccxt.get_ticker(exchange, symbol)
                    if ticker:
                        price_points.append(float(ticker['last']))
                except Exception:
                    continue
            
            if len(price_points) < 3:
                return None
            
            # Calcular momentum simple
            momentum = (price_points[-1] - price_points[0]) / price_points[0] * 100
            
            if abs(momentum) > 0.1:  # Momentum > 0.1%
                return {
                    'symbol': symbol,
                    'strategy': 'momentum',
                    'momentum': momentum,
                    'direction': 'BULLISH' if momentum > 0 else 'BEARISH',
                    'strength': abs(momentum)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error en Momentum: {e}")
            return None
    
    def create_alert(self, title, message, alert_type):
        """Crear alerta en base de datos"""
        try:
            with app.app_context():
                alert = Alert(
                    title=title,
                    message=message,
                    alert_type=alert_type,
                    created_at=datetime.utcnow()
                )
                db.session.add(alert)
                db.session.commit()
        except Exception as e:
            logger.error(f"Error creando alerta: {e}")
    
    def run_all_strategies(self):
        """Ejecutar todas las estrategias avanzadas"""
        logger.info("Ejecutando todas las estrategias avanzadas...")
        
        results = {
            'grid_opportunities': [],
            'scalping_opportunities': [],
            'pump_dump_alerts': [],
            'momentum_signals': []
        }
        
        # Grid Trading
        for symbol in self.symbols[:3]:  # Primeros 3 símbolos
            grid_result = self.grid_trading_strategy(symbol)
            if grid_result:
                results['grid_opportunities'].extend(grid_result)
        
        # Scalping
        for symbol in self.symbols[:2]:  # Primeros 2 símbolos
            scalping_result = self.scalping_strategy(symbol)
            if scalping_result:
                results['scalping_opportunities'].append(scalping_result)
        
        # Pump/Dump Detection
        pump_dump_results = self.pump_dump_detector()
        results['pump_dump_alerts'] = pump_dump_results
        
        # Momentum
        for symbol in self.symbols:
            momentum_result = self.momentum_strategy(symbol)
            if momentum_result:
                results['momentum_signals'].append(momentum_result)
        
        # Resumen
        total_opportunities = (
            len(results['grid_opportunities']) +
            len(results['scalping_opportunities']) +
            len(results['pump_dump_alerts']) +
            len(results['momentum_signals'])
        )
        
        if total_opportunities > 0:
            self.create_alert(
                "Advanced Strategies Scan Complete",
                f"Found {total_opportunities} opportunities across all strategies",
                "SUCCESS"
            )
        
        return results

if __name__ == '__main__':
    strategies = AdvancedTradingStrategies()
    results = strategies.run_all_strategies()
    print("=== ADVANCED TRADING STRATEGIES RESULTS ===")
    print(f"Grid Trading: {len(results['grid_opportunities'])} opportunities")
    print(f"Scalping: {len(results['scalping_opportunities'])} opportunities")  
    print(f"Pump/Dump: {len(results['pump_dump_alerts'])} alerts")
    print(f"Momentum: {len(results['momentum_signals'])} signals")