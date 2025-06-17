import os
import logging
import requests
from datetime import datetime
import asyncio
import threading

class TelegramBot:
    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            logging.warning("Telegram bot credentials not found. Notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
            logging.info("Telegram bot initialized successfully")

    def send_message(self, text, parse_mode='HTML'):
        """Send a message to Telegram"""
        if not self.enabled:
            logging.info(f"Telegram disabled - Would send: {text}")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logging.info("Telegram message sent successfully")
                return True
            else:
                logging.error(f"Failed to send Telegram message: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")
            return False

    def send_trade_alert(self, symbol, side, amount, price, profit_loss=None):
        """Send a formatted trade alert"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if side == 'BUY':
                emoji = "🟢"
                message = f"{emoji} <b>TRADE EXECUTED</b>\n"
                message += f"⏰ {timestamp}\n"
                message += f"📈 Symbol: <code>{symbol}</code>\n"
                message += f"💰 Side: <b>{side}</b>\n"
                message += f"💵 Amount: <b>${amount:.2f}</b>\n"
                message += f"💲 Price: <code>{price:.6f}</code>"
            else:
                emoji = "🔴" if profit_loss < 0 else "🟢"
                message = f"{emoji} <b>POSITION CLOSED</b>\n"
                message += f"⏰ {timestamp}\n"
                message += f"📉 Symbol: <code>{symbol}</code>\n"
                message += f"💰 Side: <b>{side}</b>\n"
                message += f"💵 Amount: <b>${amount:.2f}</b>\n"
                message += f"💲 Price: <code>{price:.6f}</code>\n"
                message += f"📊 P/L: <b>${profit_loss:.2f}</b>"
            
            return self.send_message(message)
            
        except Exception as e:
            logging.error(f"Error sending trade alert: {e}")
            return False

    def send_daily_summary(self, stats):
        """Send daily trading summary"""
        try:
            emoji = "📈" if stats['total_profit'] > 0 else "📉"
            
            message = f"{emoji} <b>DAILY SUMMARY</b>\n"
            message += f"📅 Date: {stats['date']}\n"
            message += f"💰 Starting Balance: <b>${stats['starting_balance']:.2f}</b>\n"
            message += f"💵 Ending Balance: <b>${stats['ending_balance']:.2f}</b>\n"
            message += f"📊 Total Trades: <b>{stats['total_trades']}</b>\n"
            message += f"✅ Successful: <b>{stats['successful_trades']}</b>\n"
            message += f"💸 Total Profit: <b>${stats['total_profit']:.2f}</b>\n"
            message += f"🏦 Fees Paid: <b>${stats['total_fees']:.2f}</b>\n"
            message += f"📈 ROI: <b>{stats['roi_percentage']:.2f}%</b>"
            
            return self.send_message(message)
            
        except Exception as e:
            logging.error(f"Error sending daily summary: {e}")
            return False

    def send_error_alert(self, error_type, error_message):
        """Send error alert"""
        try:
            message = f"🚨 <b>ERROR ALERT</b>\n"
            message += f"⚠️ Type: <b>{error_type}</b>\n"
            message += f"📝 Message: <code>{error_message}</code>\n"
            message += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return self.send_message(message)
            
        except Exception as e:
            logging.error(f"Error sending error alert: {e}")
            return False

    def send_opportunity_alert(self, symbol, spread, potential_profit):
        """Send arbitrage opportunity alert"""
        try:
            message = f"🎯 <b>ARBITRAGE OPPORTUNITY</b>\n"
            message += f"📈 Symbol: <code>{symbol}</code>\n"
            message += f"📊 Spread: <b>{spread:.3f}%</b>\n"
            message += f"💰 Potential Profit: <b>${potential_profit:.2f}</b>\n"
            message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
            
            return self.send_message(message)
            
        except Exception as e:
            logging.error(f"Error sending opportunity alert: {e}")
            return False

    def send_balance_update(self, total_balance, daily_change):
        """Send balance update"""
        try:
            emoji = "📈" if daily_change >= 0 else "📉"
            change_emoji = "🟢" if daily_change >= 0 else "🔴"
            
            message = f"{emoji} <b>BALANCE UPDATE</b>\n"
            message += f"💰 Total Balance: <b>${total_balance:.2f}</b>\n"
            message += f"{change_emoji} Daily Change: <b>${daily_change:+.2f}</b>\n"
            message += f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}"
            
            return self.send_message(message)
            
        except Exception as e:
            logging.error(f"Error sending balance update: {e}")
            return False

    def send_startup_message(self):
        """Send bot startup notification"""
        try:
            message = f"🤖 <b>TRADING BOT STARTED</b>\n"
            message += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"🎯 Strategy: Micro-Arbitrage & Scalping\n"
            message += f"💰 Target: $100/day\n"
            message += f"🔄 Status: <b>ACTIVE</b>"
            
            return self.send_message(message)
            
        except Exception as e:
            logging.error(f"Error sending startup message: {e}")
            return False

    def test_connection(self):
        """Test Telegram bot connection"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                logging.info(f"Telegram bot connected: {bot_info['result']['username']}")
                return True
            else:
                logging.error(f"Telegram bot connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Error testing Telegram connection: {e}")
            return False
