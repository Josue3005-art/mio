from flask import render_template, request, jsonify, redirect, url_for, flash
from app import app, db
from models import Trade, Balance, DailyStats, ArbitrageOpportunity, Alert, TradingConfig, User, Subscription, ReferralCode, Configuration
from datetime import datetime, timedelta
from admin_manager import admin_manager, setup_initial_admin, is_user_admin
from performance_optimizer import performance_optimizer, start_performance_optimization
from notification_system import notification_system, send_notification
# from advanced_monitoring import advanced_monitor, start_advanced_monitoring, get_system_health, get_live_metrics
from flask_login import current_user
import logging
import json

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get current balance
        balances = Balance.query.all()
        total_balance = sum(b.usd_value for b in balances)
        
        # Get today's stats
        today = datetime.now().date()
        today_stats = DailyStats.query.filter_by(date=today).first()
        
        if not today_stats:
            # Create default stats for today
            yesterday = today - timedelta(days=1)
            yesterday_stats = DailyStats.query.filter_by(date=yesterday).first()
            starting_balance = yesterday_stats.ending_balance if yesterday_stats else 30.0
            
            today_stats = DailyStats(
                date=today,
                starting_balance=starting_balance,
                ending_balance=total_balance,
                total_trades=0,
                successful_trades=0,
                total_profit=0.0,
                total_fees=0.0,
                roi_percentage=0.0
            )
            db.session.add(today_stats)
            db.session.commit()
        
        # Get recent trades (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_trades = Trade.query.filter(
            Trade.executed_at >= yesterday
        ).order_by(Trade.executed_at.desc()).limit(10).all()
        
        # Get recent alerts
        recent_alerts = Alert.query.filter_by(is_read=False).order_by(
            Alert.created_at.desc()
        ).limit(5).all()
        
        # Get recent opportunities
        recent_opportunities = ArbitrageOpportunity.query.filter_by(
            status='DETECTED'
        ).order_by(ArbitrageOpportunity.detected_at.desc()).limit(5).all()
        
        return render_template('index.html',
                             total_balance=total_balance,
                             today_stats=today_stats,
                             recent_trades=recent_trades,
                             recent_alerts=recent_alerts,
                             recent_opportunities=recent_opportunities,
                             balances=balances)
    
    except Exception as e:
        logging.error(f"Error loading dashboard: {e}")
        flash('Error loading dashboard data', 'error')
        return render_template('index.html',
                             total_balance=0,
                             today_stats=None,
                             recent_trades=[],
                             recent_alerts=[],
                             recent_opportunities=[],
                             balances=[])

@app.route('/subscription')
def subscription():
    """Página de suscripciones y pagos"""
    return render_template('subscription.html')

@app.route('/dashboard')
def dashboard():
    """Detailed dashboard with charts"""
    try:
        # Get last 30 days of stats
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        daily_stats = db.session.query(DailyStats).filter(
            DailyStats.date >= thirty_days_ago
        ).order_by(DailyStats.date.asc()).all()
        
        # Get all trades for analysis
        all_trades = Trade.query.order_by(Trade.executed_at.desc()).limit(100).all()
        
        # Calculate performance metrics
        total_trades = len(all_trades)
        profitable_trades = len([t for t in all_trades if t.profit_loss > 0])
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t.profit_loss for t in all_trades if t.profit_loss)
        total_fees = sum(t.fee for t in all_trades)
        
        # Get balances
        balances = Balance.query.all()
        total_balance = sum(b.usd_value for b in balances)
        
        # Convert DailyStats to serializable format
        daily_stats_data = []
        for stat in daily_stats:
            daily_stats_data.append({
                'date': stat.date.isoformat(),
                'starting_balance': stat.starting_balance,
                'ending_balance': stat.ending_balance,
                'total_trades': stat.total_trades,
                'successful_trades': stat.successful_trades,
                'total_profit': stat.total_profit,
                'total_fees': stat.total_fees,
                'roi_percentage': stat.roi_percentage
            })
        
        return render_template('dashboard.html',
                             daily_stats=daily_stats_data,
                             all_trades=all_trades,
                             total_trades=total_trades,
                             win_rate=win_rate,
                             total_profit=total_profit,
                             total_fees=total_fees,
                             balances=balances,
                             total_balance=total_balance)
    
    except Exception as e:
        logging.error(f"Error loading detailed dashboard: {e}")
        flash('Error loading dashboard data', 'error')
        return render_template('dashboard.html',
                             daily_stats=[],
                             all_trades=[],
                             total_trades=0,
                             win_rate=0,
                             total_profit=0,
                             total_fees=0,
                             balances=[],
                             total_balance=0)

@app.route('/settings')
def settings():
    """Settings page for bot configuration"""
    try:
        # Get current configuration
        configs = TradingConfig.query.all()
        config_dict = {config.key: config.value for config in configs}
        
        # Default values if not set
        default_config = {
            'min_trade_amount': '5.0',
            'max_trade_amount': '15.0',
            'stop_loss_percentage': '2.0',
            'target_spread': '0.5',
            'reinvestment_rate': '80.0',
            'max_positions': '3',
            'trading_enabled': 'true'
        }
        
        # Merge with defaults
        for key, default_value in default_config.items():
            if key not in config_dict:
                config_dict[key] = default_value
        
        return render_template('settings.html', config=config_dict)
    
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        flash('Error loading settings', 'error')
        return render_template('settings.html', config={})

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update bot settings"""
    try:
        # Get form data
        settings_data = {
            'min_trade_amount': request.form.get('min_trade_amount', '5.0'),
            'max_trade_amount': request.form.get('max_trade_amount', '15.0'),
            'stop_loss_percentage': request.form.get('stop_loss_percentage', '2.0'),
            'target_spread': request.form.get('target_spread', '0.5'),
            'reinvestment_rate': request.form.get('reinvestment_rate', '80.0'),
            'max_positions': request.form.get('max_positions', '3'),
            'trading_enabled': 'true' if request.form.get('trading_enabled') else 'false'
        }
        
        # Update database
        for key, value in settings_data.items():
            config = TradingConfig.query.filter_by(key=key).first()
            if config:
                config.value = value
                config.updated_at = datetime.utcnow()
            else:
                config = TradingConfig(key=key, value=value)
                db.session.add(config)
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
        
    except Exception as e:
        logging.error(f"Error updating settings: {e}")
        flash('Error updating settings', 'error')
    
    return redirect(url_for('settings_page'))

@app.route('/api/balance')
def api_balance():
    """API endpoint for current balance"""
    try:
        balances = Balance.query.all()
        balance_data = []
        total_usd = 0
        
        for balance in balances:
            balance_data.append({
                'asset': balance.asset,
                'free': balance.free_balance,
                'locked': balance.locked_balance,
                'total': balance.total_balance,
                'usd_value': balance.usd_value
            })
            total_usd += balance.usd_value
        
        return jsonify({
            'success': True,
            'balances': balance_data,
            'total_usd': total_usd
        })
    
    except Exception as e:
        logging.error(f"Error getting balance: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trades')
def api_trades():
    """API endpoint for recent trades"""
    try:
        limit = request.args.get('limit', 50, type=int)
        trades = Trade.query.order_by(Trade.executed_at.desc()).limit(limit).all()
        
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
                'executed_at': trade.executed_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'trades': trade_data
        })
    
    except Exception as e:
        logging.error(f"Error getting trades: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    """API endpoint for trading statistics"""
    try:
        # Get last 7 days of stats
        week_ago = datetime.now().date() - timedelta(days=7)
        daily_stats = db.session.query(DailyStats).filter(
            DailyStats.date >= week_ago
        ).order_by(DailyStats.date.asc()).all()
        
        stats_data = []
        for stat in daily_stats:
            stats_data.append({
                'date': stat.date.isoformat(),
                'starting_balance': stat.starting_balance,
                'ending_balance': stat.ending_balance,
                'total_trades': stat.total_trades,
                'successful_trades': stat.successful_trades,
                'total_profit': stat.total_profit,
                'roi_percentage': stat.roi_percentage
            })
        
        return jsonify({
            'success': True,
            'daily_stats': stats_data
        })
    
    except Exception as e:
        logging.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/alerts/mark_read', methods=['POST'])
def mark_alerts_read():
    """Mark alerts as read"""
    try:
        Alert.query.filter_by(is_read=False).update({'is_read': True})
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logging.error(f"Error marking alerts as read: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scan_arbitrage', methods=['POST'])
def scan_arbitrage():
    """Manually trigger arbitrage scan"""
    try:
        from stable_trading_bot import trading_bot
        opportunities_found = trading_bot.run_single_scan()
        
        return jsonify({
            'success': True,
            'message': f'Scan completed. Found {opportunities_found} opportunities.',
            'opportunities': opportunities_found
        })
    except Exception as e:
        logging.error(f"Error in manual scan: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/subscription', methods=['GET', 'POST'])
def subscription_page():
    """Subscription and plans page"""
    from saas_manager import saas_manager
    
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        flash("Debe iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for("index"))
    
    if request.method == 'POST':
        plan_type = request.form.get('plan_type')
        
        # Verificar si es administrador
        if is_user_admin(user_id):
            flash('Los administradores tienen acceso completo automáticamente', 'info')
            return redirect(url_for('subscription_page'))
        
        if plan_type in ['BASIC', 'PREMIUM']:
            success, message = admin_manager.change_user_plan(demo_user_id, plan_type)
            if success:
                flash(f'Plan actualizado a {plan_type} exitosamente', 'success')
            else:
                flash(f'Error: {message}', 'error')
        
        return redirect(url_for('subscription_page'))
    
    # Obtener información real del usuario
    try:
        user = User.query.get(user_id)
        if not user:
            # Crear usuario demo si no existe
            user = User()
            user.id = demo_user_id
            user.email = "admin@example.com"
            user.is_admin = True
            user.role = 'SUPER_ADMIN'
            db.session.add(user)
            db.session.commit()
        
        current_plan = user.get_effective_plan()
        is_admin = user.is_administrator()
        
        # Configurar stats basado en el plan real
        plan_features = saas_manager.PLAN_FEATURES.get(current_plan, saas_manager.PLAN_FEATURES['FREE'])
        
        user_stats = {
            'subscription': {
                'plan_type': current_plan,
                'plan_name': f'Plan {current_plan}',
                'monthly_fee': 0.0 if current_plan in ['FREE', 'ADMIN'] else (29.99 if current_plan == 'BASIC' else 99.99),
                'end_date': None,
                'features': plan_features,
                'is_admin': is_admin
            },
            'settings': {
                'trading_enabled': is_admin or current_plan in ['BASIC', 'PREMIUM'],
                'max_trade_amount': 1000.0 if is_admin else (100.0 if current_plan == 'PREMIUM' else 10.0),
                'risk_level': 'HIGH' if is_admin else 'LOW',
                'telegram_enabled': is_admin or current_plan in ['BASIC', 'PREMIUM']
            },
            'balance': {
                'total_usd': 0.0,
                'asset': 'USDT',
                'free_balance': 0.0
            },
            'referrals': {
                'codes': [],
                'total_uses': 0,
                'pending_commissions': 0.0
            }
        }
        
    except Exception as e:
        logging.error(f"Error getting user stats: {e}")
        # Fallback stats
        user_stats = {
            'subscription': {
                'plan_type': 'FREE',
                'plan_name': 'Plan Gratuito',
                'monthly_fee': 0.0,
                'end_date': None,
                'features': saas_manager.PLAN_FEATURES['FREE'],
                'is_admin': False
            },
            'settings': {
                'trading_enabled': False,
                'max_trade_amount': 10.0,
                'risk_level': 'LOW',
                'telegram_enabled': False
            },
            'balance': {
                'total_usd': 0.0,
                'asset': 'USDT',
                'free_balance': 0.0
            },
            'referrals': {
                'codes': [],
                'total_uses': 0,
                'pending_commissions': 0.0
            }
        }
    
    return render_template('subscription.html', 
                         user_stats=user_stats,
                         plans=saas_manager.PLAN_FEATURES)

# Rutas administrativas
@app.route('/admin')
def admin_dashboard():
    """Panel de administración"""
    demo_user_id = '1'
    if not is_user_admin(demo_user_id):
        flash('Acceso denegado - Se requieren permisos de administrador', 'error')
        return redirect(url_for('index'))
    
    try:
        success, stats = admin_manager.get_system_stats()
        success2, users = admin_manager.list_all_users()
        
        return render_template('admin_dashboard.html', 
                             stats=stats if success else {},
                             users=users if success2 else [])
    except Exception as e:
        logging.error(f"Error in admin dashboard: {e}")
        return render_template('admin_dashboard.html', stats={}, users=[])

@app.route('/admin/create_license', methods=['POST'])
def admin_create_license():
    """Crear licencia para usuario"""
    demo_user_id = '1'
    if not is_user_admin(demo_user_id):
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        user_id = request.json.get('user_id')
        plan_type = request.json.get('plan_type', 'PREMIUM')
        duration = int(request.json.get('duration', 1))
        
        success, message = admin_manager.create_license_for_user(user_id, plan_type, duration)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/make_admin', methods=['POST'])
def admin_make_admin():
    """Convertir usuario en administrador"""
    demo_user_id = '1'
    if not is_user_admin(demo_user_id):
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        user_id = request.json.get('user_id')
        success, message = admin_manager.create_admin_user(user_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/generate_code', methods=['POST'])
def admin_generate_code():
    """Generar código de referido"""
    demo_user_id = '1'
    if not is_user_admin(demo_user_id):
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        user_id = request.json.get('user_id')
        custom_code = request.json.get('custom_code')
        success, message = admin_manager.generate_referral_code(user_id, custom_code)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings')
def settings_page():
    """Settings and configuration page"""
    try:
        # Get current configuration from database
        config = {}
        config_items = TradingConfig.query.all()
        for item in config_items:
            config[item.key] = item.value
        
        return render_template('settings.html', config=config)
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        return render_template('settings.html', config={})

@app.route('/analytics')
def analytics_page():
    """Analytics and performance page"""
    try:
        # Get recent performance data
        recent_trades = Trade.query.order_by(Trade.executed_at.desc()).limit(50).all()
        
        # Calculate analytics data
        total_trades = len(recent_trades)
        successful_trades = len([t for t in recent_trades if t.profit_loss > 0])
        success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t.profit_loss for t in recent_trades)
        total_volume = sum(t.total_value for t in recent_trades)
        
        # Get daily stats for the last 7 days
        daily_stats = db.session.query(DailyStats).order_by(DailyStats.date.desc()).limit(7).all()
        
        # Get recent opportunities
        opportunities = ArbitrageOpportunity.query.order_by(ArbitrageOpportunity.id.desc()).limit(20).all()
        
        analytics_data = {
            'total_trades': total_trades,
            'successful_trades': successful_trades,
            'success_rate': success_rate,
            'total_profit': total_profit,
            'total_volume': total_volume,
            'daily_stats': daily_stats,
            'recent_trades': recent_trades[:10],
            'opportunities': opportunities
        }
        
        return render_template('analytics.html', analytics=analytics_data)
    except Exception as e:
        logging.error(f"Error loading analytics: {e}")
        return render_template('analytics.html', analytics={})



@app.route('/api/upgrade_plan', methods=['POST'])
def upgrade_plan():
    """Upgrade subscription plan"""
    try:
        data = request.get_json()
        new_plan = data.get('plan_type')
        
        if new_plan not in ['FREE', 'BASIC', 'PREMIUM']:
            return jsonify({'success': False, 'error': 'Plan inválido'}), 400
        
        # Check if trading mode is demo or real
        trading_mode_config = TradingConfig.query.filter_by(key='trading_mode').first()
        mode = trading_mode_config.value if trading_mode_config else 'demo'
        
        return jsonify({
            'success': True,
            'message': f'Plan actualizado a {new_plan} exitosamente',
            'trading_mode': mode
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle_trading_mode', methods=['POST'])
def toggle_trading_mode():
    """Toggle between demo and real trading mode"""
    try:
        data = request.get_json()
        new_mode = data.get('mode', 'demo')
        
        if new_mode not in ['demo', 'real']:
            return jsonify({'success': False, 'error': 'Modo inválido'}), 400
        
        # Check if API keys are configured for real mode
        if new_mode == 'real':
            binance_key = TradingConfig.query.filter_by(key='binance_api_key').first()
            kucoin_key = TradingConfig.query.filter_by(key='kucoin_api_key').first()
            
            if not binance_key or not kucoin_key:
                return jsonify({
                    'success': False,
                    'error': 'Para modo real necesitas configurar las API keys de los exchanges primero'
                }), 400
        
        # Update trading mode
        mode_config = TradingConfig.query.filter_by(key='trading_mode').first()
        if mode_config:
            mode_config.value = new_mode
        else:
            mode_config = TradingConfig(key='trading_mode', value=new_mode)
            db.session.add(mode_config)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Modo de trading cambiado a: {"REAL (dinero real)" if new_mode == "real" else "DEMO (simulación)"}',
            'mode': new_mode
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_trading_mode')
def get_trading_mode():
    """Get current trading mode"""
    try:
        mode_config = TradingConfig.query.filter_by(key='trading_mode').first()
        mode = mode_config.value if mode_config else 'demo'
        
        return jsonify({
            'success': True,
            'mode': mode,
            'description': 'REAL (dinero real)' if mode == 'real' else 'DEMO (simulación)'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/configure_exchange_keys', methods=['POST'])
def configure_exchange_keys():
    """Configure exchange API keys"""
    try:
        data = request.get_json()
        exchange = data.get('exchange', '').lower()
        api_key = data.get('api_key', '')
        api_secret = data.get('api_secret', '')
        passphrase = data.get('passphrase', '')  # For KuCoin
        
        if not exchange or not api_key or not api_secret:
            return jsonify({'success': False, 'error': 'Exchange, API key y secret son requeridos'}), 400
        
        if exchange not in ['binance', 'kucoin']:
            return jsonify({'success': False, 'error': 'Exchange no soportado'}), 400
        
        # Save API key
        key_config = TradingConfig.query.filter_by(key=f'{exchange}_api_key').first()
        if key_config:
            key_config.value = api_key
        else:
            key_config = TradingConfig(key=f'{exchange}_api_key', value=api_key)
            db.session.add(key_config)
        
        # Save API secret
        secret_config = TradingConfig.query.filter_by(key=f'{exchange}_api_secret').first()
        if secret_config:
            secret_config.value = api_secret
        else:
            secret_config = TradingConfig(key=f'{exchange}_api_secret', value=api_secret)
            db.session.add(secret_config)
        
        # Save passphrase for KuCoin
        if exchange == 'kucoin' and passphrase:
            passphrase_config = TradingConfig.query.filter_by(key=f'{exchange}_passphrase').first()
            if passphrase_config:
                passphrase_config.value = passphrase
            else:
                passphrase_config = TradingConfig(key=f'{exchange}_passphrase', value=passphrase)
                db.session.add(passphrase_config)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'API keys de {exchange.upper()} configuradas correctamente'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_referral', methods=['POST'])
def generate_referral():
    """Generate referral code"""
    try:
        import random
        import string
        
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        return jsonify({
            'success': True,
            'referral_code': code
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/setup_telegram', methods=['POST'])
def setup_telegram():
    """Setup Telegram alerts"""
    try:
        data = request.get_json()
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')
        
        if not bot_token or not chat_id:
            return jsonify({'success': False, 'error': 'Bot token y chat ID requeridos'}), 400
        
        from advanced_alerts import AdvancedAlertSystem
        alert_system = AdvancedAlertSystem()
        
        success = alert_system.setup_telegram(bot_token, chat_id)
        
        if success:
            test_success, test_message = alert_system.test_telegram_connection()
            
            return jsonify({
                'success': True,
                'message': 'Telegram configurado correctamente',
                'test_result': test_message
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error configurando Telegram'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/advanced_scan', methods=['POST'])
def advanced_scan():
    """Execute advanced scan with all strategies"""
    try:
        from advanced_strategies import AdvancedTradingStrategies
        from advanced_alerts import AdvancedAlertSystem
        
        strategies = AdvancedTradingStrategies()
        results = strategies.run_all_strategies()
        
        alert_system = AdvancedAlertSystem()
        alert_system.run_all_alert_checks()
        
        total_opportunities = (
            len(results.get('grid_opportunities', [])) +
            len(results.get('scalping_opportunities', [])) +
            len(results.get('pump_dump_alerts', [])) +
            len(results.get('momentum_signals', []))
        )
        
        return jsonify({
            'success': True,
            'message': f'Escaneo avanzado completado. {total_opportunities} oportunidades encontradas.',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# APIs optimizadas avanzadas
@app.route('/api/v2/dashboard')
def api_v2_dashboard():
    """API optimizada del dashboard con cache"""
    try:
        data = performance_optimizer.get_optimized_dashboard_data()
        return jsonify({
            'success': True,
            'data': data,
            'cached': True,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logging.error(f"API v2 dashboard error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/v2/notifications')
def api_v2_notifications():
    """API optimizada de notificaciones"""
    try:
        user_id = request.args.get('user_id', '1')
        limit = int(request.args.get('limit', 10))
        
        notifications = notification_system.get_user_notifications(user_id, limit)
        stats = notification_system.get_notification_stats()
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logging.error(f"API v2 notifications error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/v2/notifications/mark-read', methods=['POST'])
def api_v2_mark_notifications_read():
    """Marcar notificaciones como leídas"""
    try:
        user_id = request.json.get('user_id', '1')
        notification_ids = request.json.get('notification_ids')
        
        success, message = notification_system.mark_notifications_read(user_id, notification_ids)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"Mark notifications read error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/v2/system/health')
def api_v2_system_health():
    """API de salud del sistema simplificada"""
    try:
        # Métricas básicas sin dependencias externas
        with app.app_context():
            total_trades = Trade.query.count()
            total_alerts = Alert.query.count()
            unread_alerts = Alert.query.filter_by(is_read=False).count()
            
            health_score = 100
            if unread_alerts > 50:
                health_score -= 20
            if total_alerts > 1000:
                health_score -= 10
            
            status = 'healthy' if health_score > 70 else 'warning' if health_score > 40 else 'critical'
            
            return jsonify({
                'success': True,
                'health_score': health_score,
                'status': status,
                'metrics': {
                    'total_trades': total_trades,
                    'total_alerts': total_alerts,
                    'unread_alerts': unread_alerts,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
    except Exception as e:
        logging.error(f"System health error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/v2/performance/optimize', methods=['POST'])
def api_v2_optimize_performance():
    """Endpoint para optimización manual"""
    demo_user_id = '1'
    if not is_user_admin(demo_user_id):
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        performance_optimizer.cleanup_old_data()
        performance_optimizer.optimize_database()
        
        send_notification(
            'Optimización Manual',
            'Optimización de rendimiento ejecutada manualmente',
            'SUCCESS'
        )
        
        return jsonify({
            'success': True,
            'message': 'Optimización completada exitosamente'
        })
    except Exception as e:
        logging.error(f"Performance optimization error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/v2/cache/clear', methods=['POST'])
def api_v2_clear_cache():
    """Limpiar cache del sistema"""
    demo_user_id = '1'
    if not is_user_admin(demo_user_id):
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    try:
        cache_size = len(performance_optimizer.cache)
        performance_optimizer.cache.clear()
        
        send_notification(
            'Cache Limpiado',
            f'Cache del sistema limpiado: {cache_size} entradas removidas',
            'INFO'
        )
        
        return jsonify({
            'success': True,
            'message': f'Cache limpiado: {cache_size} entradas removidas'
        })
    except Exception as e:
        logging.error(f"Clear cache error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# === APIs DE CONFIGURACIÓN DE EXCHANGES ===
@app.route('/api/configure_api_keys', methods=['POST'])
def configure_api_keys():
    """Configurar API keys de exchanges"""
    try:
        data = request.get_json()
        exchange = data.get('exchange', '').lower()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        passphrase = data.get('passphrase', '').strip()
        
        if not exchange or not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'Exchange, API key y API secret son obligatorios'
            }), 400
        
        if exchange not in ['binance', 'kucoin']:
            return jsonify({
                'success': False,
                'error': 'Exchange no soportado. Solo Binance y KuCoin'
            }), 400
        
        # Guardar configuración
        config_data = {
            'api_key': api_key,
            'api_secret': api_secret,
            'enabled': True,
            'validated_at': datetime.now().isoformat()
        }
        
        if passphrase:
            config_data['passphrase'] = passphrase
        
        config = Configuration.query.filter_by(key=f'{exchange}_config').first()
        if config:
            config.value = json.dumps(config_data)
            config.updated_at = datetime.now()
        else:
            config = Configuration(
                key=f'{exchange}_config',
                value=json.dumps(config_data)
            )
            db.session.add(config)
        
        db.session.commit()
        
        # Crear alerta
        alert = Alert(
            title=f'Exchange {exchange.title()} Configurado',
            message=f'API keys de {exchange.title()} configuradas correctamente',
            alert_type='INFO'
        )
        db.session.add(alert)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'API keys de {exchange.title()} configuradas exitosamente',
            'exchange': exchange
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error configurando API keys: {e}")
        return jsonify({
            'success': False,
            'error': f'Error guardando configuración: {str(e)}'
        }), 500

@app.route('/api/get_trading_config')
def get_trading_config():
    """Obtener configuración de trading actual"""
    try:
        config = Configuration.query.filter_by(key='trading_mode').first()
        mode = 'demo' if not config else config.value
        
        # Verificar exchanges configurados
        binance_config = Configuration.query.filter_by(key='binance_config').first()
        kucoin_config = Configuration.query.filter_by(key='kucoin_config').first()
        
        exchanges_configured = {
            'binance': bool(binance_config),
            'kucoin': bool(kucoin_config)
        }
        
        return jsonify({
            'success': True,
            'mode': mode,
            'exchanges_configured': exchanges_configured,
            'can_enable_real': any(exchanges_configured.values())
        })
        
    except Exception as e:
        logging.error(f"Error obteniendo configuración: {e}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo configuración: {str(e)}'
        }), 500

@app.route('/api/set_trading_mode', methods=['POST'])
def set_trading_mode():
    """Cambiar modo de trading entre demo y real"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'demo')
        
        if mode not in ['demo', 'real']:
            return jsonify({
                'success': False,
                'error': 'Modo inválido. Solo "demo" o "real"'
            }), 400
        
        # Si es modo real, verificar exchanges configurados
        if mode == 'real':
            binance_config = Configuration.query.filter_by(key='binance_config').first()
            kucoin_config = Configuration.query.filter_by(key='kucoin_config').first()
            
            if not binance_config and not kucoin_config:
                return jsonify({
                    'success': False,
                    'error': 'Debes configurar al menos una API de exchange para el modo real'
                }), 400
        
        # Guardar configuración
        config = Configuration.query.filter_by(key='trading_mode').first()
        if config:
            config.value = mode
            config.updated_at = datetime.now()
        else:
            config = Configuration(
                key='trading_mode',
                value=mode
            )
            db.session.add(config)
        
        db.session.commit()
        
        # Crear alerta
        alert = Alert(
            title=f'Modo de Trading Cambiado',
            message=f'Sistema cambiado a modo {mode.upper()}',
            alert_type='INFO'
        )
        db.session.add(alert)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Modo de trading cambiado a {mode.upper()}',
            'mode': mode
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error cambiando modo: {e}")
        return jsonify({
            'success': False,
            'error': f'Error cambiando modo: {str(e)}'
        }), 500

@app.route('/api/start_real_trading', methods=['POST'])
def start_real_trading():
    """Iniciar trading real"""
    try:
        # Verificar modo real
        config = Configuration.query.filter_by(key='trading_mode').first()
        if not config or config.value != 'real':
            return jsonify({
                'success': False,
                'error': 'Debe estar en modo REAL para iniciar trading'
            }), 400
        
        # Importar y usar motor de trading real
        from real_trading_engine import start_real_trading
        result = start_real_trading()
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error iniciando trading real: {e}")
        return jsonify({
            'success': False,
            'error': f'Error iniciando trading: {str(e)}'
        }), 500

@app.route('/api/stop_real_trading', methods=['POST'])
def stop_real_trading():
    """Detener trading real"""
    try:
        from real_trading_engine import stop_real_trading
        stop_real_trading()
        
        return jsonify({
            'success': True,
            'message': 'Trading real detenido'
        })
        
    except Exception as e:
        logging.error(f"Error deteniendo trading real: {e}")
        return jsonify({
            'success': False,
            'error': f'Error deteniendo trading: {str(e)}'
        }), 500

@app.route('/api/trading_status')
def trading_status():
    """Obtener estado del trading"""
    try:
        from real_trading_engine import get_trading_status
        status = get_trading_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logging.error(f"Error obteniendo estado: {e}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo estado: {str(e)}'
        }), 500

@app.route('/api/test_exchange_connection', methods=['POST'])
def test_exchange_connection():
    """Probar conexión con exchange usando API keys temporales"""
    try:
        data = request.get_json()
        exchange = data.get('exchange')
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        passphrase = data.get('passphrase', '')
        
        if not exchange or not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'Exchange, API key y secret son obligatorios'
            }), 400
        
        # Test connection with ccxt
        import ccxt
        
        try:
            if exchange == 'binance':
                client = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
            elif exchange == 'kucoin':
                client = ccxt.kucoin({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'password': passphrase,
                    'sandbox': False,
                    'enableRateLimit': True,
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Exchange no soportado'
                }), 400
            
            # Test connection by fetching balance
            balance = client.fetch_balance()
            total_balance = balance.get('USDT', {}).get('total', 0)
            
            return jsonify({
                'success': True,
                'message': f'Conexión exitosa con {exchange.upper()}',
                'balance': f'Balance USDT: ${total_balance:.2f}' if total_balance > 0 else 'API válida'
            })
            
        except ccxt.AuthenticationError:
            return jsonify({
                'success': False,
                'error': 'API keys inválidas o permisos insuficientes'
            }), 400
        except ccxt.PermissionDenied:
            return jsonify({
                'success': False,
                'error': 'Permisos insuficientes - verifica que las APIs tengan permisos de trading'
            }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error de conexión: {str(e)}'
            }), 400
            
    except Exception as e:
        logging.error(f"Error probando conexión: {e}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500

# === SISTEMA DE PAGOS ZINLI ===
@app.route('/api/payment/plans')
def get_payment_plans():
    """Obtener planes de pago disponibles"""
    try:
        from zinli_payment_system import get_payment_processor
        processor = get_payment_processor()
        plans = processor.get_payment_plans()
        
        return jsonify({
            'success': True,
            'plans': plans
        })
        
    except Exception as e:
        logging.error(f"Error obteniendo planes: {e}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo planes: {str(e)}'
        }), 500

@app.route('/api/payment/create', methods=['POST'])
def create_payment():
    """Crear enlace de pago"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', '1')  # Usuario demo
        plan_type = data.get('plan_type')
        
        if not plan_type:
            return jsonify({
                'success': False,
                'error': 'Tipo de plan es obligatorio'
            }), 400
        
        from zinli_payment_system import get_payment_processor
        processor = get_payment_processor()
        plans = processor.get_payment_plans()
        
        if plan_type not in plans:
            return jsonify({
                'success': False,
                'error': 'Plan no válido'
            }), 400
        
        amount_usd = plans[plan_type]['price_usd']
        result = processor.create_payment_link(user_id, plan_type, amount_usd)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error creando pago: {e}")
        return jsonify({
            'success': False,
            'error': f'Error creando pago: {str(e)}'
        }), 500

@app.route('/webhook/zinli', methods=['POST'])
def zinli_webhook():
    """Webhook para confirmaciones de pago de Zinli"""
    try:
        webhook_data = request.get_json()
        
        from zinli_payment_system import get_payment_processor
        processor = get_payment_processor()
        result = processor.process_webhook(webhook_data)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error procesando webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/payment/success')
def payment_success():
    """Página de éxito de pago"""
    return render_template('payment_success.html')

@app.route('/payment/cancel')
def payment_cancel():
    """Página de cancelación de pago"""
    return render_template('payment_cancel.html')

@app.route('/api/subscription/cancel', methods=['POST'])
def cancel_subscription():
    """Cancelar suscripción"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', '1')
        
        from zinli_payment_system import get_payment_processor
        processor = get_payment_processor()
        result = processor.cancel_subscription(user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error cancelando suscripción: {e}")
        return jsonify({
            'success': False,
            'error': f'Error cancelando suscripción: {str(e)}'
        }), 500

# Inicializar sistemas de optimización al arrancar
try:
    start_performance_optimization()
    send_notification('Sistema Iniciado', 'Sistemas de optimización activados', 'SUCCESS')
    logging.info("Sistemas de optimización iniciados correctamente")
except Exception as e:
    logging.error(f"Error iniciando sistemas de optimización: {e}")

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('index.html'), 500
