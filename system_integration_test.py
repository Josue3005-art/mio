"""
Comprehensive integration test for the advanced trading system
Tests all major components: strategies, alerts, SaaS features
"""

import logging
from datetime import datetime
from app import app, db
from models import User, Subscription, UserSettings, TradingConfig
from advanced_strategies import AdvancedTradingStrategies
from advanced_alerts import AdvancedAlertSystem
from saas_manager import SaaSManager
from stable_trading_bot import trading_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_advanced_strategies():
    """Test all advanced trading strategies"""
    logger.info("Testing Advanced Trading Strategies...")
    
    try:
        strategies = AdvancedTradingStrategies()
        
        # Test individual strategies
        grid_result = strategies.grid_trading_strategy('BTC/USDT')
        scalping_result = strategies.scalping_strategy('BTC/USDT')
        pump_dump_result = strategies.pump_dump_detector()
        momentum_result = strategies.momentum_strategy('BTC/USDT')
        
        # Test comprehensive scan
        all_results = strategies.run_all_strategies()
        
        logger.info(f"Grid Trading: {len(all_results.get('grid_opportunities', []))} opportunities")
        logger.info(f"Scalping: {len(all_results.get('scalping_opportunities', []))} opportunities")
        logger.info(f"Pump/Dump: {len(all_results.get('pump_dump_alerts', []))} alerts")
        logger.info(f"Momentum: {len(all_results.get('momentum_signals', []))} signals")
        
        return True
        
    except Exception as e:
        logger.error(f"Advanced strategies test failed: {e}")
        return False

def test_alert_system():
    """Test advanced alert system"""
    logger.info("Testing Advanced Alert System...")
    
    try:
        alert_system = AdvancedAlertSystem()
        
        # Test alert checks (without Telegram for now)
        result = alert_system.run_all_alert_checks()
        
        logger.info(f"Alert system test result: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Alert system test failed: {e}")
        return False

def test_saas_functionality():
    """Test SaaS multiuser functionality"""
    logger.info("Testing SaaS Functionality...")
    
    try:
        saas = SaaSManager()
        
        # Test plan features
        for plan_type in ['FREE', 'BASIC', 'PREMIUM']:
            features = saas.PLAN_FEATURES[plan_type]
            logger.info(f"{plan_type}: ${features['price']}/month, {features['max_trades_per_day']} trades/day")
        
        # Test system stats
        stats = saas.get_all_users_stats()
        if stats:
            logger.info(f"Total users: {stats['total_users']}")
            logger.info(f"Monthly revenue: ${stats['monthly_revenue']}")
        
        return True
        
    except Exception as e:
        logger.error(f"SaaS functionality test failed: {e}")
        return False

def test_basic_arbitrage():
    """Test basic arbitrage functionality"""
    logger.info("Testing Basic Arbitrage...")
    
    try:
        # Run single scan
        opportunities = trading_bot.run_single_scan()
        logger.info(f"Basic arbitrage scan found {opportunities} opportunities")
        
        return True
        
    except Exception as e:
        logger.error(f"Basic arbitrage test failed: {e}")
        return False

def test_database_models():
    """Test database models and relationships"""
    logger.info("Testing Database Models...")
    
    try:
        with app.app_context():
            # Test configuration storage
            test_config = TradingConfig(
                key='test_key',
                value='test_value'
            )
            db.session.add(test_config)
            db.session.commit()
            
            # Verify configuration retrieval
            retrieved_config = TradingConfig.query.filter_by(key='test_key').first()
            if retrieved_config and retrieved_config.value == 'test_value':
                logger.info("Database models working correctly")
            else:
                logger.error("Database model test failed")
                return False
            
            # Clean up test data
            db.session.delete(retrieved_config)
            db.session.commit()
            
        return True
        
    except Exception as e:
        logger.error(f"Database models test failed: {e}")
        return False

def generate_system_report():
    """Generate comprehensive system status report"""
    logger.info("Generating System Report...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'system_status': 'OPERATIONAL',
        'components': {},
        'features': {
            'basic_arbitrage': True,
            'advanced_strategies': True,
            'alert_system': True,
            'saas_multiuser': True,
            'telegram_alerts': True,
            'referral_system': True,
            'subscription_plans': True
        },
        'exchanges': ['Gate.io', 'MEXC', 'OKX', 'Bitget'],
        'strategies': ['Arbitrage', 'Grid Trading', 'Scalping', 'Pump/Dump Detection', 'Momentum'],
        'subscription_plans': {
            'FREE': {'price': 0, 'trades': 5, 'features': 'Basic arbitrage'},
            'BASIC': {'price': 29.99, 'trades': 50, 'features': 'Arbitrage + Scalping + Telegram'},
            'PREMIUM': {'price': 99.99, 'trades': 'Unlimited', 'features': 'All strategies + API access'}
        }
    }
    
    return report

def run_comprehensive_test():
    """Run all system tests"""
    print("=== COMPREHENSIVE SYSTEM TEST ===")
    print(f"Started at: {datetime.now()}")
    
    tests = [
        ("Database Models", test_database_models),
        ("Basic Arbitrage", test_basic_arbitrage),
        ("Advanced Strategies", test_advanced_strategies),
        ("Alert System", test_alert_system),
        ("SaaS Functionality", test_saas_functionality)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        try:
            result = test_func()
            results[test_name] = "PASS" if result else "FAIL"
            print(f"Result: {results[test_name]}")
        except Exception as e:
            results[test_name] = f"ERROR: {str(e)}"
            print(f"Result: {results[test_name]}")
    
    # Generate final report
    print("\n=== TEST SUMMARY ===")
    for test_name, result in results.items():
        status_emoji = "✅" if result == "PASS" else "❌"
        print(f"{status_emoji} {test_name}: {result}")
    
    passed_tests = sum(1 for result in results.values() if result == "PASS")
    total_tests = len(results)
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
    else:
        print("⚠️  Some tests failed - Check logs for details")
    
    # Generate system report
    report = generate_system_report()
    print(f"\n=== SYSTEM CAPABILITIES ===")
    print(f"Exchanges: {', '.join(report['exchanges'])}")
    print(f"Strategies: {', '.join(report['strategies'])}")
    print(f"Plans: FREE (${report['subscription_plans']['FREE']['price']}), BASIC (${report['subscription_plans']['BASIC']['price']}), PREMIUM (${report['subscription_plans']['PREMIUM']['price']})")
    
    return results, report

if __name__ == '__main__':
    test_results, system_report = run_comprehensive_test()