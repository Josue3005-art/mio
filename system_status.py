from app import app, db
from models import Trade, Alert, DailyStats
from datetime import datetime, timedelta

def get_system_status():
    """Get comprehensive system status"""
    with app.app_context():
        # Trading statistics
        today = datetime.now().date()
        today_trades = Trade.query.filter(
            Trade.executed_at >= datetime.combine(today, datetime.min.time())
        ).all()
        
        total_trades_today = len(today_trades)
        profitable_trades = len([t for t in today_trades if t.profit_loss and t.profit_loss > 0])
        total_profit_today = sum(t.profit_loss for t in today_trades if t.profit_loss) or 0
        
        # Recent alerts
        recent_alerts = Alert.query.filter_by(is_read=False).count()
        
        # System capabilities
        exchanges_available = ['Gate.io', 'MEXC', 'OKX', 'Bitget']
        symbols_monitored = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        
        # Performance metrics
        win_rate = (profitable_trades / total_trades_today * 100) if total_trades_today > 0 else 0
        
        return {
            'status': 'ACTIVE',
            'exchanges': exchanges_available,
            'symbols': symbols_monitored,
            'today_stats': {
                'trades': total_trades_today,
                'profit': total_profit_today,
                'win_rate': win_rate
            },
            'alerts': recent_alerts,
            'capital': 30.0,
            'mode': 'SIMULATION'
        }

if __name__ == '__main__':
    status = get_system_status()
    print("=== CRYPTO ARBITRAGE BOT STATUS ===")
    print(f"Status: {status['status']}")
    print(f"Mode: {status['mode']}")
    print(f"Capital: ${status['capital']}")
    print(f"Exchanges: {', '.join(status['exchanges'])}")
    print(f"Symbols: {', '.join(status['symbols'])}")
    print(f"Today: {status['today_stats']['trades']} trades, ${status['today_stats']['profit']:.4f} profit")
    print(f"Win Rate: {status['today_stats']['win_rate']:.1f}%")
    print(f"Pending Alerts: {status['alerts']}")