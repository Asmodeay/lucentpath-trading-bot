import os
from dotenv import load_dotenv

load_dotenv()

COINBASE_API_KEY = os.getenv('COINBASE_API_KEY', '')
COINBASE_SECRET = os.getenv('COINBASE_SECRET', '')

# Trading Configuration - LIVE MODE WITH SAFETY
DEFAULT_CONFIG = {
    'exchanges': [
        {
            'name': 'coinbase',
            'api_key': COINBASE_API_KEY,
            'secret': COINBASE_SECRET,
            'sandbox': True  # This enables our safety mode even though Coinbase doesn't support sandbox
        }
    ],
    'strategies': [
        {
            'type': 'sma_crossover',
            'fast_period': 10,
            'slow_period': 20
        },
        {
            'type': 'rsi',
            'period': 14,
            'oversold': 30,
            'overbought': 70
        }
    ],
    'symbols': [
        {'symbol': 'BTC-USD', 'exchange': 'coinbase'},
        {'symbol': 'ETH-USD', 'exchange': 'coinbase'},
        {'symbol': 'ADA-USD', 'exchange': 'coinbase'},
        {'symbol': 'SOL-USD', 'exchange': 'coinbase'},
        {'symbol': 'MATIC-USD', 'exchange': 'coinbase'}
    ],
    'cycle_interval': 300,
    'risk_management': {
        'max_position_size': 0.1,
        'max_daily_loss': 0.05,
        'risk_per_trade': 0.02
    }
}
