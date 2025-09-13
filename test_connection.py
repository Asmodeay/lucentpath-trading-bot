from core_engine import ExchangeConnector
import os
from dotenv import load_dotenv
import ccxt

# Load environment variables from .env file
load_dotenv()

def check_available_exchanges():
    """Check what exchanges are available in ccxt"""
    print("🔍 Available exchanges in ccxt:")
    available = ccxt.exchanges
    binance_variants = [ex for ex in available if 'binance' in ex.lower()]
    coinbase_variants = [ex for ex in available if 'coinbase' in ex.lower()]
    
    print(f"   Binance variants: {binance_variants}")
    print(f"   Coinbase variants: {coinbase_variants}")
    return binance_variants, coinbase_variants

def test_exchange_connection():
    """Test connection to exchanges using API keys"""
    
    print("🔗 Testing Exchange Connections...")
    print("=" * 50)
    
    # First, check what exchanges are available
    binance_variants, coinbase_variants = check_available_exchanges()
    
    # Test Binance US Connection
    print("\n📊 Testing Binance US Connection:")
    binance_api_key = os.getenv('BINANCE_API_KEY')
    binance_secret = os.getenv('BINANCE_SECRET')
    
    if not binance_api_key or not binance_secret:
        print("❌ Binance API keys not found in .env file")
        print("   Please add BINANCE_API_KEY and BINANCE_SECRET to your .env file")
    else:
        # Try different approaches for Binance US
        success = False
        
        # Method 1: Try binanceus directly
        if 'binanceus' in binance_variants:
            try:
                print("   🇺🇸 Trying Binance US specific endpoint...")
                exchange = ccxt.binanceus({
                    'apiKey': binance_api_key,
                    'secret': binance_secret,
                    'sandbox': True,
                    'enableRateLimit': True,
                })
                markets = exchange.load_markets()
                print(f"✅ Binance US connection successful!")
                print(f"   📈 {len(markets)} markets available")
                success = True
                
                # Test market data
                try:
                    ohlcv = exchange.fetch_ohlcv('BTC/USD', '1h', limit=10)
                    if ohlcv:
                        latest_price = ohlcv[-1][4]  # Close price
                        print(f"   📊 Market data fetch successful")
                        print(f"   💵 Latest BTC price: ${latest_price:,.2f}")
                except Exception as e:
                    print(f"   ⚠️ Market data fetch failed: {e}")
                
            except Exception as e:
                print(f"   ❌ Binance US specific failed: {e}")
        
        # Method 2: Try regular binance with US settings
        if not success and 'binance' in binance_variants:
            try:
                print("   🌍 Trying regular Binance with US settings...")
                exchange = ccxt.binance({
                    'apiKey': binance_api_key,
                    'secret': binance_secret,
                    'sandbox': False,  # Binance US doesn't have testnet
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',  # US only supports spot trading
                    }
                })
                
                # Override URLs for Binance US
                exchange.urls['api'] = {
                    'public': 'https://api.binance.us/api/v3',
                    'private': 'https://api.binance.us/api/v3',
                }
                
                markets = exchange.load_markets()
                print(f"✅ Binance US (modified) connection successful!")
                print(f"   📈 {len(markets)} markets available")
                success = True
                
                # Test market data
                try:
                    ohlcv = exchange.fetch_ohlcv('BTC/USD', '1h', limit=10)
                    if ohlcv:
                        latest_price = ohlcv[-1][4]
                        print(f"   📊 Market data fetch successful")
                        print(f"   💵 Latest BTC price: ${latest_price:,.2f}")
                except Exception as e:
                    print(f"   ⚠️ Market data fetch failed: {e}")
                    
            except Exception as e:
                print(f"   ❌ Modified Binance failed: {e}")
                if "restricted location" in str(e).lower():
                    print("   🌍 This appears to be a geographic restriction issue")
                    print("   💡 Solutions:")
                    print("      - Use a VPN to a supported location")
                    print("      - Contact Binance US support")
                    print("      - Use Coinbase Pro instead (US-friendly)")
        
        if not success:
            print("   ❌ All Binance connection methods failed")
            print("   🔧 Troubleshooting:")
            print("      1. Verify your API keys are for Binance US (not regular Binance)")
            print("      2. Check if trading is enabled on your API keys")
            print("      3. Try using Coinbase Pro instead")
    
    # Test Coinbase Pro Connection
    print("\n🏦 Testing Coinbase Pro Connection:")
    coinbase_api_key = os.getenv('COINBASE_API_KEY')
    coinbase_secret = os.getenv('COINBASE_SECRET')
    coinbase_passphrase = os.getenv('COINBASE_PASSPHRASE')
    
    if not coinbase_api_key or not coinbase_secret:
        print("❌ Coinbase API keys not found in .env file")
        print("   Please add COINBASE_API_KEY, COINBASE_SECRET, and COINBASE_PASSPHRASE to your .env file")
    else:
        # Try different Coinbase exchange names
        coinbase_names = ['coinbasepro', 'coinbase', 'gdax']
        success = False
        
        for exchange_name in coinbase_names:
            if exchange_name in coinbase_variants:
                try:
                    print(f"   🏦 Trying {exchange_name}...")
                    
                    if exchange_name == 'coinbasepro' or exchange_name == 'gdax':
                        exchange = getattr(ccxt, exchange_name)({
                            'apiKey': coinbase_api_key,
                            'secret': coinbase_secret,
                            'password': coinbase_passphrase,  # Coinbase uses 'password' for passphrase
                            'sandbox': True,
                            'enableRateLimit': True,
                        })
                    else:
                        exchange = getattr(ccxt, exchange_name)({
                            'apiKey': coinbase_api_key,
                            'secret': coinbase_secret,
                            'enableRateLimit': True,
                        })
                    
                    markets = exchange.load_markets()
                    print(f"✅ {exchange_name.title()} connection successful!")
                    print(f"   📈 {len(markets)} markets available")
                    success = True
                    
                    # Test market data
                    try:
                        # Try different symbol formats
                        symbols_to_try = ['BTC/USD', 'BTC-USD', 'BTCUSD']
                        for symbol in symbols_to_try:
                            try:
                                ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=10)
                                if ohlcv:
                                    latest_price = ohlcv[-1][4]
                                    print(f"   📊 Market data fetch successful ({symbol})")
                                    print(f"   💵 Latest BTC price: ${latest_price:,.2f}")
                                    break
                            except:
                                continue
                    except Exception as e:
                        print(f"   ⚠️ Market data fetch failed: {e}")
                    
                    break
                    
                except Exception as e:
                    print(f"   ❌ {exchange_name} failed: {e}")
        
        if not success:
            print("   ❌ All Coinbase connection methods failed")
            print("   🔧 Troubleshooting:")
            print("      1. Verify you're using Coinbase Pro (not regular Coinbase)")
            print("      2. Make sure you have all three: API Key, Secret, and Passphrase")
            print("      3. Check API permissions include 'View' and 'Trade'")

def create_updated_core_engine():
    """Create an updated version of the core engine with proper exchange support"""
    print("\n🔧 Creating updated core_engine.py...")
    
    updated_code = '''
# Updated ExchangeConnector class for core_engine.py

def _initialize_exchange(self):
    """Initialize exchange connection with proper US support"""
    try:
        if self.exchange_name.lower() in ['binance', 'binanceus']:
            # Handle Binance US specifically
            if 'binanceus' in ccxt.exchanges:
                exchange = ccxt.binanceus({
                    'apiKey': self.api_key,
                    'secret': self.secret,
                    'sandbox': self.sandbox,
                    'enableRateLimit': True,
                })
            else:
                # Fallback to regular binance with US endpoints
                exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.secret,
                    'sandbox': False,  # Binance US doesn't have testnet
                    'enableRateLimit': True,
                })
                # Override URLs for Binance US
                exchange.urls['api'] = {
                    'public': 'https://api.binance.us/api/v3',
                    'private': 'https://api.binance.us/api/v3',
                }
                
        elif self.exchange_name.lower() in ['coinbase', 'coinbasepro', 'gdax']:
            # Try different Coinbase variants
            if 'coinbasepro' in ccxt.exchanges:
                exchange = ccxt.coinbasepro({
                    'apiKey': self.api_key,
                    'secret': self.secret,
                    'password': self.passphrase,  # Add passphrase support
                    'sandbox': self.sandbox,
                    'enableRateLimit': True,
                })
            elif 'gdax' in ccxt.exchanges:
                exchange = ccxt.gdax({
                    'apiKey': self.api_key,
                    'secret': self.secret,
                    'password': self.passphrase,
                    'sandbox': self.sandbox,
                    'enableRateLimit': True,
                })
            else:
                raise ValueError("No Coinbase exchange variant available")
        else:
            raise ValueError(f"Unsupported exchange: {self.exchange_name}")
        
        # Test connection
        exchange.load_markets()
        logger.info(f"Successfully connected to {self.exchange_name}")
        return exchange
        
    except Exception as e:
        logger.error(f"Failed to connect to {self.exchange_name}: {e}")
        raise
'''
    
    print("📝 Add this code to your ExchangeConnector class in core_engine.py")
    print("   Replace the _initialize_exchange method with the code above")

if __name__ == "__main__":
    print("🚀 CryptoBot Fixed Connection Test")
    print("Diagnosing and fixing connection issues...")
    
    # Test exchange connections
    test_exchange_connection()
    
    # Provide updated code
    create_updated_core_engine()
    
    print("\n" + "=" * 50)
    print("✅ Diagnostic test complete!")
    print("\n💡 Key Issues Found:")
    print("   1. Binance testnet is geo-restricted")
    print("   2. Coinbase Pro naming has changed in newer ccxt versions")
    print("\n🔧 Solutions:")
    print("   1. For Binance: Use live API (start with small amounts)")
    print("   2. For Coinbase: Add passphrase to your .env file")
    print("   3. Consider using VPN if in restricted location")
    print("\n📝 Update your .env file to include:")
    print("   COINBASE_PASSPHRASE=your_coinbase_passphrase")
