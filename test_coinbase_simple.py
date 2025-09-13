from core_engine import ExchangeConnector, TradingBot
import os
from dotenv import load_dotenv

load_dotenv()

def test_simple_coinbase():
    """Test Coinbase connection without passphrase"""
    
    print("🚀 Testing Coinbase (No Passphrase)")
    print("=" * 40)
    
    api_key = os.getenv('COINBASE_API_KEY')
    secret = os.getenv('COINBASE_SECRET')
    
    if not api_key or not secret:
        print("❌ Missing COINBASE_API_KEY or COINBASE_SECRET")
        print("Add them to your .env file:")
        print("COINBASE_API_KEY=your_api_key")
        print("COINBASE_SECRET=your_secret")
        return False
    
    try:
        # Test connection (NO PASSPHRASE!)
        connector = ExchangeConnector('coinbase', api_key, secret, sandbox=True)
        print("✅ Coinbase connection successful!")
        
        # Test market data
        btc_data = connector.get_candles('BTC-USD', '1h', 10)
        if not btc_data.empty:
            price = btc_data['close'].iloc[-1]
            print(f"✅ BTC-USD price: ${price:,.2f}")
        
        eth_data = connector.get_candles('ETH-USD', '1h', 10)  
        if not eth_data.empty:
            price = eth_data['close'].iloc[-1]
            print(f"✅ ETH-USD price: ${price:,.2f}")
            
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_trading_bot():
    """Test the full trading bot setup"""
    
    print("\n🤖 Testing Trading Bot")
    print("=" * 40)
    
    config = {
        'exchanges': [
            {
                'name': 'coinbase',
                'api_key': os.getenv('COINBASE_API_KEY'),
                'secret': os.getenv('COINBASE_SECRET'),
                'sandbox': True
            }
        ],
        'strategies': [
            {
                'type': 'sma_crossover',
                'fast_period': 10,
                'slow_period': 20
            }
        ],
        'symbols': [
            {'symbol': 'BTC-USD', 'exchange': 'coinbase'},
            {'symbol': 'ETH-USD', 'exchange': 'coinbase'}
        ],
        'cycle_interval': 300
    }
    
    try:
        bot = TradingBot(config)
        print("✅ Trading bot created successfully!")
        
        # Test analysis
        signals = bot.analyze_symbol('BTC-USD', 'coinbase')
        print(f"✅ Analysis complete: {len(signals)} signals generated")
        
        if signals:
            for signal in signals:
                print(f"   🎯 {signal.action.value.upper()} at ${signal.price:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trading bot test failed: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Simple Coinbase Test (No Passphrase Required)")
    
    if test_simple_coinbase():
        if test_trading_bot():
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Ready to proceed with web dashboard!")
        else:
            print("\n❌ Trading bot test failed")
    else:
        print("\n❌ Basic connection test failed")
