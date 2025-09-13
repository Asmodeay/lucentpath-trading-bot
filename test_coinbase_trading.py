from core_engine import TradingBot, ExchangeConnector
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def test_coinbase_trading_setup():
    """Test the complete trading setup with Coinbase"""
    
    print("🚀 Testing Coinbase Trading Setup")
    print("=" * 50)
    
    # Test configuration
    config = {
        'exchanges': [
            {
                'name': 'coinbase',
                'api_key': os.getenv('COINBASE_API_KEY'),
                'secret': os.getenv('COINBASE_SECRET'),
                'passphrase': os.getenv('COINBASE_PASSPHRASE'),
                'sandbox': True  # Safe mode
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
            {'symbol': 'ADA-USD', 'exchange': 'coinbase'}
        ],
        'cycle_interval': 300
    }
    
    # Test 1: Exchange Connection
    print("\n📡 Test 1: Exchange Connection")
    try:
        connector = ExchangeConnector(
            'coinbase',
            os.getenv('COINBASE_API_KEY'),
            os.getenv('COINBASE_SECRET'),
            os.getenv('COINBASE_PASSPHRASE'),
            sandbox=True
        )
        print("✅ Exchange connector created successfully")
        
        # Test balance
        balance = connector.get_balance()
        if balance:
            print("✅ Balance fetch successful")
            print(f"   Available currencies: {list(balance.get('total', {}).keys())[:5]}")
        else:
            print("⚠️ Balance fetch returned empty (normal for sandbox)")
            
    except Exception as e:
        print(f"❌ Exchange connection failed: {e}")
        return False
    
    # Test 2: Market Data
    print("\n📊 Test 2: Market Data Fetch")
    try:
        for symbol_config in config['symbols']:
            symbol = symbol_config['symbol']
            df = connector.get_candles(symbol, '1h', 20)
            
            if not df.empty:
                latest_price = df['close'].iloc[-1]
                print(f"✅ {symbol}: ${latest_price:,.2f} ({len(df)} candles)")
            else:
                print(f"❌ {symbol}: No data returned")
                
    except Exception as e:
        print(f"❌ Market data test failed: {e}")
        return False
    
    # Test 3: Strategy Analysis
    print("\n🧠 Test 3: Strategy Analysis")
    try:
        bot = TradingBot(config)
        print("✅ Trading bot created successfully")
        
        # Test signal generation for each symbol
        for symbol_config in config['symbols']:
            symbol = symbol_config['symbol']
            exchange_name = symbol_config['exchange']
            
            print(f"\n   Analyzing {symbol}...")
            signals = bot.analyze_symbol(symbol, exchange_name)
            
            if signals:
                for signal in signals:
                    print(f"   🔥 Signal: {signal.action.value.upper()} at ${signal.price:.2f}")
                    print(f"      Strategy: {signal.strategy.value}")
                    print(f"      Confidence: {signal.confidence:.1%}")
            else:
                print(f"   📊 No signals generated (normal market conditions)")
                
    except Exception as e:
        print(f"❌ Strategy analysis failed: {e}")
        return False
    
    # Test 4: Bot Configuration
    print("\n⚙️ Test 4: Bot Configuration")
    try:
        stats = bot.get_performance_stats()
        print("✅ Performance stats accessible")
        print(f"   Configuration loaded: {len(config['strategies'])} strategies, {len(config['symbols'])} symbols")
        
    except Exception as e:
        print(f"❌ Bot configuration test failed: {e}")
        return False
    
    return True

def run_safe_analysis_cycle():
    """Run one safe analysis cycle (no trading)"""
    
    print("\n🔄 Running Safe Analysis Cycle")
    print("=" * 50)
    print("⚠️ SAFE MODE: Analysis only, no trades will be executed")
    
    config = {
        'exchanges': [
            {
                'name': 'coinbase',
                'api_key': os.getenv('COINBASE_API_KEY'),
                'secret': os.getenv('COINBASE_SECRET'),
                'passphrase': os.getenv('COINBASE_PASSPHRASE'),
                'sandbox': True
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
            {'symbol': 'SOL-USD', 'exchange': 'coinbase'}
        ],
        'cycle_interval': 300
    }
    
    try:
        bot = TradingBot(config)
        
        # Run analysis without executing trades
        print("\n🔍 Analyzing all symbols...")
        all_signals = []
        
        for symbol_config in config['symbols']:
            symbol = symbol_config['symbol']
            exchange_name = symbol_config['exchange']
            
            print(f"\n📈 {symbol}:")
            signals = bot.analyze_symbol(symbol, exchange_name)
            
            if signals:
                for signal in signals:
                    print(f"   🎯 {signal.action.value.upper()} signal at ${signal.price:.2f}")
                    print(f"      Strategy: {signal.strategy.value}")
                    print(f"      Confidence: {signal.confidence:.1%}")
                    print(f"      Time: {signal.timestamp}")
                    all_signals.append(signal)
            else:
                print(f"   📊 No signals (market conditions don't meet strategy criteria)")
        
        print(f"\n📋 Analysis Summary:")
        print(f"   Total signals generated: {len(all_signals)}")
        if all_signals:
            buy_signals = [s for s in all_signals if s.action.value == 'buy']
            sell_signals = [s for s in all_signals if s.action.value == 'sell']
            print(f"   Buy signals: {len(buy_signals)}")
            print(f"   Sell signals: {len(sell_signals)}")
        
        print(f"\n✅ Analysis cycle completed successfully!")
        print(f"🛡️ No trades executed (safe mode)")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis cycle failed: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Coinbase Trading Bot Test Suite")
    print("Testing all components before live deployment")
    
    # Check environment variables
    required_vars = ['COINBASE_API_KEY', 'COINBASE_SECRET', 'COINBASE_PASSPHRASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please add them to your .env file")
        exit(1)
    
    # Run tests
    print("\n🧪 Running Component Tests...")
    if test_coinbase_trading_setup():
        print("\n✅ All component tests passed!")
        
        print("\n🚀 Running Live Analysis Test...")
        if run_safe_analysis_cycle():
            print("\n🎉 ALL TESTS PASSED!")
            print("\n📋 Next Steps:")
            print("   1. ✅ Coinbase connection working")
            print("   2. ✅ Strategies analyzing markets")
            print("   3. ✅ Bot configuration valid")
            print("   4. 🚀 Ready for web dashboard setup")
            print("   5. 💰 Ready for small live trading tests")
            print("\n⚠️ When ready for live trading:")
            print("   - Start with small amounts ($10-50)")
            print("   - Monitor closely for first few trades")
            print("   - Set sandbox=False in config")
        else:
            print("\n❌ Analysis test failed")
    else:
        print("\n❌ Component tests failed")
        print("Please fix the issues above before proceeding")
