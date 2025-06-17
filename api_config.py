import os
from app import db
from models import TradingConfig

def setup_api_keys():
    """Configurar claves API en la base de datos"""
    
    api_keys = {
        'binance_api_key': os.environ.get('BINANCE_API_KEY'),
        'binance_api_secret': os.environ.get('BINANCE_API_SECRET'),
        'kucoin_api_key': os.environ.get('KUCOIN_API_KEY'),
        'kucoin_api_secret': os.environ.get('KUCOIN_API_SECRET'),
        'kucoin_passphrase': os.environ.get('KUCOIN_PASSPHRASE'),
    }
    
    for key, value in api_keys.items():
        if not value:
            print(f"WARNING: Environment variable {key.upper()} is not set. API key will not be available.")
    print("API key setup check completed.")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        setup_api_keys()