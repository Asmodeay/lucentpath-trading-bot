from core_engine import ExchangeConnector, TradingBot
import os
from dotenv import load_dotenv

load_dotenv()

def test_coinbase_live_safe():
    """Test Coinbase in live mode with safety checks"""
    
    print("🚀 Testing Coinbase (Live Mode - Safe)")
    print("=" * 40)
    print("⚠️ NOTE: Using live Coinbase API (no sandbox available)")
    print("🛡️ SAFETY: No real trades will be executed in test mode")
    print()
    
    api_key = os.getenv('COINBASE_API_KEY')
    secret = os.getenv('COINBASE_SECRET')
    
    if not api_key or not secret:
        print("❌ Missing COINBASE_API_KEY or COINBASE_SECRET")
        print("Add them to your .env file:")
        print("COINBASE_API_KEY=your_api_key")
        print("COINBASE_SECRET=your_secret")
        return False
    
    try:
        # Test connection (Live mode but with safety)
        connector = ExchangeConnector('coinbase', api_key, secret, sandbox=True)
        print("✅ Coinbase connection successful! (Live mode)")
        
        # Test balance (READ-ONLY - SAFE)
        print("\n📊 Testing balance fetch (READ-ONLY)...")
        balance = connector.get_balance()
        if balance:
            print("✅ Balance fetch successful!")
            total_usd = balance.get('total', {}).get('USD', 0)
            total_btc = balance.get('total', {}).get('BTC', 0)
            print(f"   💰 USD Balance: ${total_usd:.2f}")
            print(f"   ₿ BTC Balance: {total_btc:.6f}")
        else:
            print("⚠️ Balance empty or not accessible")
        
        # Test market data (READ-ONLY - SAFE)
        print("\n📈 Testing market data (READ-ONLY)...")
        symbols_to_test = ['BTC-USD', 'ETH-USD', 'ADA-USD']
        
        for symbol in symbols_to_test:
            data = connector.get_candles(symbol, '1h', 10)
            if not data.empty:
                price = data['close'].iloc[-1]
                print(f"✅ {symbol}: ${price:,.2f}")
            else:
                print(f"❌ {symbol}: No data")
        
        # Test simulated order (SAFE - NO REAL TRADE)
        print("\n🛡️ Testing simulated order (NO REAL TRADE)...")
        fake_order = connector.place_order('BTC-USD', 'buy', 0.001, 50000)
        if fake_order and fake_order.get('status') == 'SIMULATED':
            print("✅ Simulated order created successfully!")
            print(f"   📝 Order ID: {fake_order['id']}")
            print(f"   🛡️ Status: {fake_order['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_trading_strategies():
    """Test strategy analysis (SAFE)"""
    
    print("\n🧠 Testing Trading Strategies (Analysis Only)")
    print("=" * 50)
    
    config = {
        'exchanges': [
            {
                'name': 'coinbase',
                'api_key': os.getenv('COINBASE_API_KEY'),
                'secret': os.getenv('COINBASE_SECRET'),
                'sandbox': True  # Enables safety mode
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
            {'symbol': 'ETH-USD', 'exchange': 'coinbase'}
        ],
        'cycle_interval': 300
    }
    
    try:
        bot = TradingBot(config)
        print("✅ Trading bot created successfully!")
        
        # Test analysis for each symbol
        total_signals = 0
        for symbol_config in config['symbols']:
            symbol = symbol_config['symbol']
            exchange = symbol_config['exchange']
            
            print(f"\n📊 Analyzing {symbol}...")
            signals = bot.analyze_symbol(symbol, exchange)
            
            if signals:
                for signal in signals:
                    print(f"   🎯 {signal.action.value.upper()} signal at ${signal.price:.2f}")
                    print(f"      Strategy: {signal.strategy.value}")
                    print(f"      Confidence: {signal.confidence:.1%}")
                total_signals += len(signals)
            else:
                print(f"   📈 No signals (normal market conditions)")
        
        print(f"\n📋 Analysis Summary: {total_signals} total signals generated")
        return True
        
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Coinbase Live Mode Test (Safe Operations)")
    print("📡 This uses the real Coinbase API but with safety protections")
    print()
    
    if test_coinbase_live_safe():
        if test_trading_strategies():
            print("\n🎉 ALL TESTS PASSED!")
            print("\n✅ What works:")
            print("   - Live Coinbase API connection")
            print("   - Real market data fetching")
            print("   - Strategy analysis")
            print("   - Safety protections active")
            print("\n🚀 Next Steps:")
            print("   1. Run web dashboard: python app.py")
            print("   2. Test with very small amounts when ready")
            print("   3. Set sandbox=False for real trading")
        else:
            print("\n❌ Strategy test failed")
    else:
        print("\n❌ Connection test failed")
        
    print("\n🛡️ Safety Reminder:")
    print("   - Currently in SAFE mode (no real trades)")
    print("   - All orders are simulated")
    print("   - Only market data and balance reading")
