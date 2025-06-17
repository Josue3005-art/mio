from app import db
from datetime import datetime
from sqlalchemy import func
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# User models for authentication (required for SaaS)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='USER')  # USER, ADMIN, SUPER_ADMIN
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_administrator(self):
        return self.is_admin or self.role in ['ADMIN', 'SUPER_ADMIN']
    
    def can_manage_system(self):
        return self.role == 'SUPER_ADMIN'
    
    def get_effective_plan(self):
        """Obtener plan efectivo - admins tienen acceso completo"""
        if self.is_administrator():
            return 'ADMIN'
        
        subscription = Subscription.query.filter_by(
            user_id=self.id, 
            status='ACTIVE'
        ).first()
        
        return subscription.plan_type if subscription else 'FREE'

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)
    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class TradingConfig(db.Model):
    """Configuration settings for the trading bot"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value

class Trade(db.Model):
    """Record of executed trades"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # BUY or SELL
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    strategy = db.Column(db.String(50), nullable=False)  # arbitrage, scalping, grid
    profit_loss = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='EXECUTED')
    exchange = db.Column(db.String(20), default='BINANCE')
    order_id = db.Column(db.String(100))
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, symbol=None, side=None, quantity=0.0, price=0.0, total_value=0.0, 
                 fee=0.0, strategy=None, profit_loss=0.0, status='EXECUTED', 
                 exchange='BINANCE', order_id=None):
        if symbol: self.symbol = symbol
        if side: self.side = side
        if quantity: self.quantity = quantity
        if price: self.price = price
        if total_value: self.total_value = total_value
        if fee: self.fee = fee
        if strategy: self.strategy = strategy
        if profit_loss: self.profit_loss = profit_loss
        if status: self.status = status
        if exchange: self.exchange = exchange
        if order_id: self.order_id = order_id

class ArbitrageOpportunity(db.Model):
    """Detected arbitrage opportunities"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    sell_price = db.Column(db.Float, nullable=False)
    spread_percentage = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)
    potential_profit = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='DETECTED')  # DETECTED, EXECUTED, EXPIRED
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime)

class Balance(db.Model):
    """Account balance tracking"""
    id = db.Column(db.Integer, primary_key=True)
    asset = db.Column(db.String(10), nullable=False)
    free_balance = db.Column(db.Float, nullable=False)
    locked_balance = db.Column(db.Float, default=0.0)
    total_balance = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float, nullable=False)
    exchange = db.Column(db.String(20), default='BINANCE')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, asset=None, free_balance=0.0, locked_balance=0.0, 
                 total_balance=0.0, usd_value=0.0, exchange='BINANCE'):
        if asset: self.asset = asset
        if free_balance: self.free_balance = free_balance
        if locked_balance: self.locked_balance = locked_balance
        if total_balance: self.total_balance = total_balance
        if usd_value: self.usd_value = usd_value
        if exchange: self.exchange = exchange

class DailyStats(db.Model):
    """Daily trading statistics"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    starting_balance = db.Column(db.Float, nullable=False)
    ending_balance = db.Column(db.Float, nullable=False)
    total_trades = db.Column(db.Integer, default=0)
    successful_trades = db.Column(db.Integer, default=0)
    total_profit = db.Column(db.Float, default=0.0)
    total_fees = db.Column(db.Float, default=0.0)
    roi_percentage = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, date=None, starting_balance=None, ending_balance=None, 
                 total_trades=0, successful_trades=0, total_profit=0.0, 
                 total_fees=0.0, roi_percentage=0.0):
        self.date = date
        self.starting_balance = starting_balance
        self.ending_balance = ending_balance
        self.total_trades = total_trades
        self.successful_trades = successful_trades
        self.total_profit = total_profit
        self.total_fees = total_fees
        self.roi_percentage = roi_percentage

class Alert(db.Model):
    """System alerts and notifications"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR, SUCCESS
    is_read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)  # Asociar con usuario
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, title=None, message=None, alert_type=None, user_id=None):
        self.title = title
        self.message = message
        self.alert_type = alert_type
        self.user_id = user_id

class Subscription(db.Model):
    """User subscription plans"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    plan_type = db.Column(db.String(20), nullable=False)  # FREE, BASIC, PREMIUM
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, CANCELLED, EXPIRED
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    monthly_fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='subscriptions')
    
    def __init__(self, user_id=None, plan_type=None, status='ACTIVE', 
                 start_date=None, end_date=None, monthly_fee=0.0):
        self.user_id = user_id
        self.plan_type = plan_type
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
        self.monthly_fee = monthly_fee

class UserTrade(db.Model):
    """User-specific trades"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    strategy = db.Column(db.String(50), nullable=False)
    profit_loss = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='EXECUTED')
    exchange = db.Column(db.String(20), default='SIMULATION')
    order_id = db.Column(db.String(100))
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='trades')

class UserBalance(db.Model):
    """User-specific balance tracking"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    asset = db.Column(db.String(10), nullable=False)
    free_balance = db.Column(db.Float, nullable=False)
    locked_balance = db.Column(db.Float, default=0.0)
    total_balance = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float, nullable=False)
    exchange = db.Column(db.String(20), default='SIMULATION')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='balances')
    
    def __init__(self, user_id=None, asset=None, free_balance=0.0, locked_balance=0.0, 
                 total_balance=0.0, usd_value=0.0, exchange='SIMULATION'):
        self.user_id = user_id
        self.asset = asset
        self.free_balance = free_balance
        self.locked_balance = locked_balance
        self.total_balance = total_balance
        self.usd_value = usd_value
        self.exchange = exchange

class UserSettings(db.Model):
    """User-specific trading settings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    trading_enabled = db.Column(db.Boolean, default=False)
    max_trade_amount = db.Column(db.Float, default=10.0)
    risk_level = db.Column(db.String(10), default='LOW')  # LOW, MEDIUM, HIGH
    preferred_exchanges = db.Column(db.Text, default='gateio,mexc')  # JSON string
    preferred_symbols = db.Column(db.Text, default='BTC/USDT,ETH/USDT')  # JSON string
    telegram_enabled = db.Column(db.Boolean, default=False)
    telegram_chat_id = db.Column(db.String(100), nullable=True)
    
    def __init__(self, user_id=None, trading_enabled=False, max_trade_amount=10.0, 
                 risk_level='LOW', preferred_exchanges='gateio,mexc', 
                 preferred_symbols='BTC/USDT,ETH/USDT', telegram_enabled=False, 
                 telegram_chat_id=None):
        self.user_id = user_id
        self.trading_enabled = trading_enabled
        self.max_trade_amount = max_trade_amount
        self.risk_level = risk_level
        self.preferred_exchanges = preferred_exchanges
        self.preferred_symbols = preferred_symbols
        self.telegram_enabled = telegram_enabled
        self.telegram_chat_id = telegram_chat_id
    email_alerts = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='settings')

class ReferralCode(db.Model):
    """Referral system for commissions"""
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    uses_count = db.Column(db.Integer, default=0)
    total_commission = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    referrer = db.relationship('User', backref='referral_codes')
    
    def __init__(self, referrer_id=None, code=None, uses_count=0, 
                 total_commission=0.0, is_active=True):
        self.referrer_id = referrer_id
        self.code = code
        self.uses_count = uses_count
        self.total_commission = total_commission
        self.is_active = is_active

class Commission(db.Model):
    """Commission tracking"""
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    referred_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    referral_code_id = db.Column(db.Integer, db.ForeignKey('referral_code.id'), nullable=False)
    commission_amount = db.Column(db.Float, nullable=False)
    commission_type = db.Column(db.String(20), nullable=False)  # SIGNUP, MONTHLY, TRADE
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PAID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='earned_commissions')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='generated_commissions')
    referral_code = db.relationship('ReferralCode', backref='commissions')
    
    def __init__(self, referrer_id=None, referred_id=None, referral_code_id=None, 
                 commission_amount=0.0, commission_type=None, status='PENDING', paid_at=None):
        self.referrer_id = referrer_id
        self.referred_id = referred_id
        self.referral_code_id = referral_code_id
        self.commission_amount = commission_amount
        self.commission_type = commission_type
        self.status = status
        self.paid_at = paid_at

class Configuration(db.Model):
    """Configuración general del sistema"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, key=None, value=None, description=None):
        self.key = key
        self.value = value
        self.description = description
