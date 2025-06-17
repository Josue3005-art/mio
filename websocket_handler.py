from flask_socketio import emit, disconnect
from app import socketio, db
from models import Trade, Balance, Alert
import logging
from datetime import datetime

@socketio.on('connect')
def on_connect():
    """Handle client connection"""
    logging.info('Client connected to WebSocket')
    emit('status', {'msg': 'Connected to Trading Bot'})

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection"""
    logging.info('Client disconnected from WebSocket')

@socketio.on('get_balance')
def handle_get_balance():
    """Send current balance to client"""
    try:
        balances = Balance.query.all()
        total_usd = sum(b.usd_value for b in balances)
        
        balance_data = []
        for balance in balances:
            if balance.total_balance > 0:
                balance_data.append({
                    'asset': balance.asset,
                    'free': balance.free_balance,
                    'locked': balance.locked_balance,
                    'total': balance.total_balance,
                    'usd_value': balance.usd_value
                })
        
        emit('balance_update', {
            'total_usd': total_usd,
            'balances': balance_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error sending balance update: {e}")
        emit('error', {'message': 'Failed to get balance data'})

@socketio.on('get_recent_trades')
def handle_get_recent_trades():
    """Send recent trades to client"""
    try:
        trades = Trade.query.order_by(Trade.executed_at.desc()).limit(10).all()
        
        trade_data = []
        for trade in trades:
            trade_data.append({
                'id': trade.id,
                'symbol': trade.symbol,
                'side': trade.side,
                'quantity': trade.quantity,
                'price': trade.price,
                'total_value': trade.total_value,
                'profit_loss': trade.profit_loss,
                'strategy': trade.strategy,
                'executed_at': trade.executed_at.strftime('%H:%M:%S')
            })
        
        emit('trades_update', {
            'trades': trade_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error sending trades update: {e}")
        emit('error', {'message': 'Failed to get trades data'})

@socketio.on('get_alerts')
def handle_get_alerts():
    """Send unread alerts to client"""
    try:
        alerts = Alert.query.filter_by(is_read=False).order_by(
            Alert.created_at.desc()
        ).limit(5).all()
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'type': alert.alert_type,
                'created_at': alert.created_at.strftime('%H:%M:%S')
            })
        
        emit('alerts_update', {
            'alerts': alert_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error sending alerts update: {e}")
        emit('error', {'message': 'Failed to get alerts data'})

@socketio.on('mark_alert_read')
def handle_mark_alert_read(data):
    """Mark specific alert as read"""
    try:
        alert_id = data.get('alert_id')
        if alert_id:
            alert = Alert.query.get(alert_id)
            if alert:
                alert.is_read = True
                db.session.commit()
                emit('alert_marked_read', {'alert_id': alert_id})
        
    except Exception as e:
        logging.error(f"Error marking alert as read: {e}")
        emit('error', {'message': 'Failed to mark alert as read'})

# Custom events emitted by the trading engine
def emit_balance_update(total_usd, balances=None):
    """Emit balance update to all connected clients"""
    try:
        socketio.emit('balance_update', {
            'total_usd': total_usd,
            'balances': balances or [],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error emitting balance update: {e}")

def emit_trade_executed(trade_data):
    """Emit trade execution to all connected clients"""
    try:
        socketio.emit('trade_executed', {
            'trade': trade_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error emitting trade execution: {e}")

def emit_new_alert(title, message, alert_type):
    """Emit new alert to all connected clients"""
    try:
        socketio.emit('new_alert', {
            'title': title,
            'message': message,
            'type': alert_type,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error emitting new alert: {e}")

def emit_opportunity_detected(opportunity):
    """Emit arbitrage opportunity to all connected clients"""
    try:
        socketio.emit('opportunity_detected', {
            'opportunity': opportunity,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error emitting opportunity: {e}")

def emit_system_status(status, message):
    """Emit system status update"""
    try:
        socketio.emit('system_status', {
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error emitting system status: {e}")
