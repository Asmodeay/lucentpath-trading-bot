from core_engine import TradingBot, ExchangeConnector
import os
from dotenv import load_dotenv
import traceback
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

def test_bot_step_by_step():
    """Test each component separately to find the issue"""
    
    print("🔍 DEBUGGING BOT STARTUP ISSUE")
    print("=" * 50)
    
    # Step 1: Test Exchange Connection
    print("\n1️⃣ Testing Exchange Connection...")
    try:
        connector = ExchangeConnector(
            'coinbase',
            os.getenv('COINBASE_API_KEY'),
            os.getenv('COINBASE_SECRET'),
            sandbox=True
        )
        print("✅ Exchange connector created")
        
        # Test market data
        df = connector.get_candles('BTC-USD', '1h', 10)
        if not df.empty:
            print(f"✅ Market data working: {len(df)} candles")
        else:
            print("❌ No market data returned")
            return False
            
    except Exception as e:
        print(f"❌ Exchange connection failed: {e}")
        traceback.print_exc()
        return False
    
    # Step 2: Test Bot Configuration
    print("\n2️⃣ Testing Bot Configuration...")
    try:
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
                    'fast_period': 5,  # Smaller periods for testing
                    'slow_period': 10
                }
            ],
            'symbols': [
                {'symbol': 'BTC-USD', 'exchange': 'coinbase'}
            ],
            'cycle_interval': 60  # 1 minute for testing
        }
        
        print("✅ Configuration created")
        
        # Step 3: Create Bot
        print("\n3️⃣ Creating Trading Bot...")
        bot = TradingBot(config)
        print("✅ Bot created successfully")
        
        # Step 4: Test Single Analysis
        print("\n4️⃣ Testing Single Analysis...")
        signals = bot.analyze_symbol('BTC-USD', 'coinbase')
        print(f"✅ Analysis complete: {len(signals)} signals generated")
        
        if signals:
            for signal in signals:
                print(f"   🎯 Signal: {signal.action.value} {signal.symbol} at ${signal.price:.2f}")
        
        # Step 5: Test One Cycle
        print("\n5️⃣ Testing One Analysis Cycle...")
        bot.run_analysis_cycle()
        print("✅ Analysis cycle completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot testing failed: {e}")
        traceback.print_exc()
        return False

def test_web_bot_start():
    """Test the bot start process like the web app does"""
    
    print("\n🌐 TESTING WEB BOT START PROCESS")
    print("=" * 50)
    
    try:
        # Simulate what happens when user clicks "Start Bot"
        
        # 1. Check API keys exist
        api_key = os.getenv('COINBASE_API_KEY')
        secret = os.getenv('COINBASE_SECRET')
        
        if not api_key or not secret:
            print("❌ Missing API keys in environment")
            return False
        
        print("✅ API keys found")
        
        # 2. Create minimal config
        config = {
            'exchanges': [
                {
                    'name': 'coinbase',
                    'api_key': api_key,
                    'secret': secret,
                    'sandbox': True
                }
            ],
            'strategies': [
                {'type': 'sma_crossover', 'fast_period': 5, 'slow_period': 10}
            ],
            'symbols': [
                {'symbol': 'BTC-USD', 'exchange': 'coinbase'}
            ],
            'cycle_interval': 60
        }
        
        # 3. Try to create and start bot
        print("Creating bot...")
        bot = TradingBot(config)
        
        print("Testing bot startup...")
        # Instead of bot.start(), test the components
        
        # Test exchange initialization
        for exchange_config in config['exchanges']:
            print(f"Testing {exchange_config['name']} exchange...")
            if exchange_config['name'] in bot.exchanges:
                print(f"✅ {exchange_config['name']} exchange ready")
            else:
                print(f"❌ {exchange_config['name']} exchange failed")
                return False
        
        # Test strategies
        print(f"Testing {len(bot.strategies)} strategies...")
        if bot.strategies:
            print("✅ Strategies loaded")
        else:
            print("❌ No strategies loaded")
            return False
        
        print("✅ Bot appears ready to start")
        return True
        
    except Exception as e:
        print(f"❌ Web bot start test failed: {e}")
        traceback.print_exc()
        return False

def test_continuous_mode():
    """Test if bot can run continuously for a short time"""
    
    print("\n⏰ TESTING CONTINUOUS MODE (30 seconds)")
    print("=" * 50)
    
    try:
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
                {'type': 'sma_crossover', 'fast_period': 5, 'slow_period': 10}
            ],
            'symbols': [
                {'symbol': 'BTC-USD', 'exchange': 'coinbase'}
            ],
            'cycle_interval': 10  # 10 seconds for testing
        }
        
        bot = TradingBot(config)
        
        # Override the execute_signal method to prevent real trading
        original_execute = bot.execute_signal
        def safe_execute(signal, exchange_name):
            print(f"🎯 SIGNAL: {signal.action.value.upper()} {signal.symbol} at ${signal.price:.2f} (SIMULATED)")
        
        bot.execute_signal = safe_execute
        
        print("Starting bot for 30 seconds...")
        
        import threading
        import time
        
        # Start bot in thread
        def run_bot():
            try:
                # Run for just a few cycles
                for i in range(3):
                    print(f"Cycle {i+1}/3...")
                    bot.run_analysis_cycle()
                    time.sleep(10)
                print("✅ Bot ran successfully for 3 cycles")
            except Exception as e:
                print(f"❌ Bot failed during continuous run: {e}")
                traceback.print_exc()
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()
        bot_thread.join(timeout=35)
        
        if bot_thread.is_alive():
            print("⚠️ Bot still running after timeout")
        else:
            print("✅ Bot completed test cycles")
        
        return True
        
    except Exception as e:
        print(f"❌ Continuous mode test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 BOT DIAGNOSTIC TOOL")
    print("Finding why your bot stops immediately...")
    
    # Run all tests
    test1 = test_bot_step_by_step()
    test2 = test_web_bot_start()
    test3 = test_continuous_mode()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC RESULTS:")
    print(f"   Step-by-step test: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Web bot start test: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Continuous mode test: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your bot should work fine. The issue might be in the web interface.")
    else:
        print("\n🚨 ISSUES FOUND!")
        print("Check the error messages above to see what's failing.")


# Also create a simple bot start/stop simulator for web testing
def simulate_web_bot():
    """Simulate what the web interface does"""
    
    print("\n🌐 SIMULATING WEB INTERFACE BOT START")
    print("=" * 50)
    
    # This is what should happen when user clicks "Start Bot"
    try:
        # 1. Get user's config from database (simulated)
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
                {'type': 'sma_crossover', 'fast_period': 10, 'slow_period': 20}
            ],
            'symbols': [
                {'symbol': 'BTC-USD', 'exchange': 'coinbase'}
            ],
            'cycle_interval': 300
        }
        
        # 2. Create bot
        print("Creating bot with user config...")
        bot = TradingBot(config)
        
        # 3. Start bot (this is where it probably fails)
        print("Starting bot...")
        
        # Instead of bot.start(), let's see what fails
        print("Checking bot components...")
        
        if not bot.exchanges:
            print("❌ No exchanges configured")
            return False
        
        if not bot.strategies:
            print("❌ No strategies configured")
            return False
        
        print("✅ Bot components look good")
        
        # Try one analysis cycle
        print("Testing analysis cycle...")
        bot.run_analysis_cycle()
        print("✅ Analysis cycle works")
        
        return True
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        traceback.print_exc()
        return False

# Run simulation if called directly
if __name__ == "__main__":
    simulate_web_bot()