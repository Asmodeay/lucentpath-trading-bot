# trading_bot/core_engine.py
import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OrderType(Enum):
    BUY = "buy"
    SELL = "sell"

class StrategyType(Enum):
    SMA_CROSSOVER = "sma_crossover"
    RSI_OVERSOLD = "rsi_oversold"

@dataclass
class TradeSignal:
    symbol: str
    action: OrderType
    price: float
    quantity: float
    strategy: StrategyType
    confidence: float
    timestamp: datetime

class RiskManager:
    """Handles risk management and position sizing"""
    
    def __init__(self, max_position_size: float = 0.1, max_daily_loss: float = 0.05):
        self.max_position_size = max_position_size  # Max % of portfolio per trade
        self.max_daily_loss = max_daily_loss        # Max daily loss %
        self.daily_pnl = 0.0
        self.daily_reset_time = datetime.now().date()
    
    def calculate_position_size(self, balance: float, price: float, risk_per_trade: float = 0.02) -> float:
        """Calculate position size based on risk management rules"""
        # Reset daily PnL if new day
        if datetime.now().date() > self.daily_reset_time:
            self.daily_pnl = 0.0
            self.daily_reset_time = datetime.now().date()
        
        # Check if daily loss limit reached
        if abs(self.daily_pnl) >= self.max_daily_loss * balance:
            logger.warning("Daily loss limit reached. No new trades.")
            return 0.0
        
        # Calculate position size (risk-based)
        risk_amount = balance * risk_per_trade
        position_size = risk_amount / price
        
        # Apply maximum position size limit
        max_position_value = balance * self.max_position_size
        max_position_size = max_position_value / price
        
        return min(position_size, max_position_size)
    
    def update_pnl(self, pnl: float):
        """Update daily PnL tracking"""
        self.daily_pnl += pnl

class TradingStrategy:
    """Base class for all trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.required_candles = 50  # Minimum candles needed for analysis
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        """Override this method in strategy implementations"""
        raise NotImplementedError

class SMAStrategy(TradingStrategy):
    """Simple Moving Average Crossover Strategy"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        super().__init__("SMA_Crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.required_candles = max(fast_period, slow_period) + 5
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        if len(df) < self.required_candles:
            return None
        
        # Calculate moving averages
        df['sma_fast'] = df['close'].rolling(window=self.fast_period).mean()
        df['sma_slow'] = df['close'].rolling(window=self.slow_period).mean()
        
        current_fast = df['sma_fast'].iloc[-1]
        current_slow = df['sma_slow'].iloc[-1]
        prev_fast = df['sma_fast'].iloc[-2]
        prev_slow = df['sma_slow'].iloc[-2]
        
        current_price = df['close'].iloc[-1]
        
        # Buy signal: fast MA crosses above slow MA
        if prev_fast <= prev_slow and current_fast > current_slow:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.BUY,
                price=current_price,
                quantity=0,  # Will be calculated by risk manager
                strategy=StrategyType.SMA_CROSSOVER,
                confidence=0.7,
                timestamp=datetime.now()
            )
        
        # Sell signal: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and current_fast < current_slow:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.SELL,
                price=current_price,
                quantity=0,
                strategy=StrategyType.SMA_CROSSOVER,
                confidence=0.7,
                timestamp=datetime.now()
            )
        
        return None

class RSIStrategy(TradingStrategy):
    """RSI Oversold/Overbought Strategy"""
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSI_Strategy")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.required_candles = period + 10
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        if len(df) < self.required_candles:
            return None
        
        df['rsi'] = self.calculate_rsi(df['close'])
        current_rsi = df['rsi'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Buy signal: RSI oversold
        if current_rsi < self.oversold:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.BUY,
                price=current_price,
                quantity=0,
                strategy=StrategyType.RSI_OVERSOLD,
                confidence=0.6,
                timestamp=datetime.now()
            )
        
        # Sell signal: RSI overbought
        elif current_rsi > self.overbought:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.SELL,
                price=current_price,
                quantity=0,
                strategy=StrategyType.RSI_OVERSOLD,
                confidence=0.6,
                timestamp=datetime.now()
            )
        
        return None

class ExchangeConnector:
    """Handles connections to different exchanges - Live mode with safety checks"""
    
    def __init__(self, exchange_name: str, api_key: str, secret: str, sandbox: bool = True):
        self.exchange_name = exchange_name.lower()
        self.api_key = api_key
        self.secret = secret
        self.sandbox = sandbox  # We'll track this but Coinbase doesn't support it
        self.exchange = self._initialize_exchange()
        
    def _initialize_exchange(self):
        """Initialize exchange connection - handles no sandbox gracefully"""
        try:
            if self.exchange_name in ['binance', 'binanceus']:
                # Binance US handling (when geographic restrictions resolved)
                if hasattr(ccxt, 'binanceus'):
                    exchange = ccxt.binanceus({
                        'apiKey': self.api_key,
                        'secret': self.secret,
                        'sandbox': self.sandbox,
                        'enableRateLimit': True,
                    })
                else:
                    exchange = ccxt.binance({
                        'apiKey': self.api_key,
                        'secret': self.secret,
                        'sandbox': False,
                        'enableRateLimit': True,
                    })
                    exchange.urls['api'] = {
                        'public': 'https://api.binance.us/api/v3',
                        'private': 'https://api.binance.us/api/v3',
                    }
                    
            elif self.exchange_name in ['coinbase', 'coinbaseadvanced']:
                # Coinbase - NO SANDBOX AVAILABLE, use live mode
                exchange_variants = ['coinbaseadvanced', 'coinbase']
                
                exchange = None
                for variant in exchange_variants:
                    if hasattr(ccxt, variant):
                        try:
                            # Create exchange without sandbox (Coinbase doesn't support it)
                            exchange = getattr(ccxt, variant)({
                                'apiKey': self.api_key,
                                'secret': self.secret,
                                'enableRateLimit': True,
                                # NO SANDBOX - Coinbase doesn't support it
                            })
                            
                            logger.info(f"Using {variant} for Coinbase connection (LIVE MODE)")
                            if self.sandbox:
                                logger.warning("⚠️ Coinbase doesn't support sandbox mode - using LIVE mode")
                                logger.warning("⚠️ We'll only do READ-ONLY operations until you're ready")
                            break
                            
                        except Exception as e:
                            logger.warning(f"{variant} failed, trying next variant: {e}")
                            continue
                
                if not exchange:
                    raise ValueError("No working Coinbase exchange variant found")
                    
            else:
                raise ValueError(f"Unsupported exchange: {self.exchange_name}")
            
            # Test connection
            exchange.load_markets()
            logger.info(f"Successfully connected to {self.exchange_name}")
            return exchange
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.exchange_name}: {e}")
            raise
    
    def get_balance(self) -> Dict:
        """Get account balance - SAFE READ-ONLY"""
        try:
            balance = self.exchange.fetch_balance()
            logger.info("✅ Balance fetched successfully (READ-ONLY)")
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}
    
    def get_candles(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV candle data - SAFE READ-ONLY"""
        try:
            # Handle different symbol formats
            if self.exchange_name in ['coinbase', 'coinbaseadvanced']:
                if '/' in symbol:
                    symbol = symbol.replace('/', '-')
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            logger.info(f"✅ Market data fetched for {symbol} (READ-ONLY)")
            return df
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return pd.DataFrame()
    
    def place_order(self, symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        """Place an order - WITH SAFETY CHECKS"""
    
        # SAFETY CHECK: Don't place real orders if in "sandbox" mode
        if self.sandbox and self.exchange_name in ['coinbase', 'coinbaseadvanced']:
            logger.warning("🛡️ SAFETY MODE: Not placing real order")
            logger.warning(f"🛡️ Would place: {side.upper()} {amount} {symbol} at ${price if price else 'MARKET'}")
        
            # Return a simulated order
            return {
                'id': f'SIMULATED_ORDER_{int(time.time())}',
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'SIMULATED',
                'timestamp': datetime.now().isoformat(),
                'info': 'This is a simulated order - no real trade executed'
            }
    
        # If not in safety mode, place real order
        try:
            if self.exchange_name in ['coinbase', 'coinbaseadvanced']:
                if '/' in symbol:
                    symbol = symbol.replace('/', '-')
        
            if price:
                order = self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                order = self.exchange.create_market_order(symbol, side, amount)
        
            logger.info(f"🚨 REAL ORDER PLACED: {order}")
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {}
        
class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.exchanges = {}
        self.strategies = []
        self.risk_manager = RiskManager()
        self.is_running = False
        self.trade_history = []
        
        # Initialize exchanges
        self._initialize_exchanges()
        
        # Initialize strategies
        self._initialize_strategies()
    
    def _initialize_exchanges(self):
        """Initialize exchange connections"""
        for exchange_config in self.config.get('exchanges', []):
            try:
                connector = ExchangeConnector(
                    exchange_config['name'],
                    exchange_config['api_key'],
                    exchange_config['secret'],
                    exchange_config.get('sandbox', True)
                )
                self.exchanges[exchange_config['name']] = connector
                logger.info(f"Exchange {exchange_config['name']} initialized")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_config['name']}: {e}")
    
    def _initialize_strategies(self):
        """Initialize trading strategies"""
        strategy_configs = self.config.get('strategies', [])
        
        for strategy_config in strategy_configs:
            if strategy_config['type'] == 'sma_crossover':
                strategy = SMAStrategy(
                    strategy_config.get('fast_period', 10),
                    strategy_config.get('slow_period', 20)
                )
                self.strategies.append(strategy)
            elif strategy_config['type'] == 'rsi':
                strategy = RSIStrategy(
                    strategy_config.get('period', 14),
                    strategy_config.get('oversold', 30),
                    strategy_config.get('overbought', 70)
                )
                self.strategies.append(strategy)
    
    def analyze_symbol(self, symbol: str, exchange_name: str) -> List[TradeSignal]:
        """Analyze a symbol and generate signals"""
        signals = []
        
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not available")
            return signals
        
        exchange = self.exchanges[exchange_name]
        
        # Get candle data
        df = exchange.get_candles(symbol)
        if df.empty:
            return signals
        
        # Run each strategy
        for strategy in self.strategies:
            try:
                signal = strategy.generate_signal(df.copy(), symbol)
                if signal:
                    signals.append(signal)
                    logger.info(f"Signal generated: {strategy.name} - {signal.action.value} {symbol}")
            except Exception as e:
                logger.error(f"Error in strategy {strategy.name}: {e}")
        
        return signals
    
    def execute_signal(self, signal: TradeSignal, exchange_name: str):
        """Execute a trading signal"""
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not available")
            return
        
        exchange = self.exchanges[exchange_name]
        
        # Get current balance
        balance = exchange.get_balance()
        if not balance:
            logger.error("Could not fetch balance")
            return
        
        # Calculate position size
        total_balance = balance.get('total', {}).get('USDT', 0) or balance.get('total', {}).get('USD', 0)
        if total_balance <= 0:
            logger.error("Insufficient balance")
            return
        
        position_size = self.risk_manager.calculate_position_size(total_balance, signal.price)
        if position_size <= 0:
            logger.warning("Position size too small or risk limits exceeded")
            return
        
        # Execute trade
        try:
            order = exchange.place_order(
                signal.symbol,
                signal.action.value,
                position_size
            )
            
            if order:
                # Record trade
                trade_record = {
                    'timestamp': signal.timestamp,
                    'symbol': signal.symbol,
                    'action': signal.action.value,
                    'price': signal.price,
                    'quantity': position_size,
                    'strategy': signal.strategy.value,
                    'order_id': order.get('id')
                }
                self.trade_history.append(trade_record)
                logger.info(f"Trade executed: {trade_record}")
                
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
    
    def run_analysis_cycle(self):
        """Run one analysis cycle for all symbols"""
        symbols = self.config.get('symbols', [])
        
        for symbol_config in symbols:
            symbol = symbol_config['symbol']
            exchange_name = symbol_config['exchange']
            
            logger.info(f"Analyzing {symbol} on {exchange_name}")
            
            # Generate signals
            signals = self.analyze_symbol(symbol, exchange_name)
            
            # Execute signals
            for signal in signals:
                self.execute_signal(signal, exchange_name)
                
                # Add small delay between trades
                time.sleep(1)
    
    def start(self):
        """Start the trading bot"""
        logger.info("Starting trading bot...")
        self.is_running = True
        
        while self.is_running:
            try:
                self.run_analysis_cycle()
                
                # Wait before next cycle
                sleep_time = self.config.get('cycle_interval', 300)  # Default 5 minutes
                logger.info(f"Cycle complete. Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                self.stop()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.is_running = False
    
    def get_performance_stats(self) -> Dict:
        """Calculate performance statistics"""
        if not self.trade_history:
            return {}
        
        df = pd.DataFrame(self.trade_history)
        
        stats = {
            'total_trades': len(df),
            'buy_trades': len(df[df['action'] == 'buy']),
            'sell_trades': len(df[df['action'] == 'sell']),
            'strategies_used': df['strategy'].unique().tolist(),
            'symbols_traded': df['symbol'].unique().tolist(),
            'trading_period': {
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max()
            }
        }
        
        return stats

# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    config = {
        'exchanges': [
            {
                'name': 'binance',
                'api_key': 'your_binance_api_key',
                'secret': 'your_binance_secret',
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
            {'symbol': 'BTC/USDT', 'exchange': 'binance'},
            {'symbol': 'ETH/USDT', 'exchange': 'binance'}
        ],
        'cycle_interval': 300  # 5 minutes
    }
    
    # Create and run bot
    bot = TradingBot(config)
    
    # For testing, just run one analysis cycle
    print("Running test analysis cycle...")
    bot.run_analysis_cycle()
    
    # Print performance stats
    stats = bot.get_performance_stats()
    print("Performance Stats:", json.dumps(stats, indent=2, default=str))