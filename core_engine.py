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
from enhanced_risk_management import RiskManager, Position, PositionStatus, save_positions, load_positions

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
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    FAIR_VALUE_GAP = "fair_value_gap"

class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"

@dataclass
class TradeSignal:
    symbol: str
    action: OrderType
    price: float
    quantity: float
    strategy: StrategyType
    confidence: float
    timestamp: datetime

class Position:
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    entry_price: float
    current_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    
    def update_current_price(self, price: float):
        self.current_price = price
        if self.side == 'buy':
            self.unrealized_pnl = (price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.size

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

class FairValueGapStrategy(TradingStrategy):
    """Fair Value Gap Strategy - Identifies imbalances in price action"""
    
    def __init__(self, lookback_period: int = 20, min_gap_size: float = 0.002):
        super().__init__("Fair_Value_Gap")
        self.lookback_period = lookback_period
        self.min_gap_size = min_gap_size  # Minimum gap size as percentage
        self.required_candles = lookback_period + 5
    
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Identify fair value gaps in the price data"""
        gaps = []
        
        for i in range(2, len(df) - 1):
            # Check for bullish gap (gap up)
            if (df['low'].iloc[i] > df['high'].iloc[i-2] and 
                df['low'].iloc[i-1] > df['high'].iloc[i-2]):
                
                gap_size = (df['low'].iloc[i] - df['high'].iloc[i-2]) / df['close'].iloc[i-2]
                if gap_size >= self.min_gap_size:
                    gaps.append({
                        'type': 'bullish',
                        'gap_low': df['high'].iloc[i-2],
                        'gap_high': df['low'].iloc[i],
                        'gap_size': gap_size,
                        'index': i,
                        'filled': False
                    })
            
            # Check for bearish gap (gap down)
            elif (df['high'].iloc[i] < df['low'].iloc[i-2] and 
                  df['high'].iloc[i-1] < df['low'].iloc[i-2]):
                
                gap_size = (df['low'].iloc[i-2] - df['high'].iloc[i]) / df['close'].iloc[i-2]
                if gap_size >= self.min_gap_size:
                    gaps.append({
                        'type': 'bearish',
                        'gap_low': df['high'].iloc[i],
                        'gap_high': df['low'].iloc[i-2],
                        'gap_size': gap_size,
                        'index': i,
                        'filled': False
                    })
        
        return gaps
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        if len(df) < self.required_candles:
            return None
        
        gaps = self.identify_fair_value_gaps(df)
        if not gaps:
            return None
        
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Check for gap fill opportunities
        for gap in gaps[-3:]:  # Check last 3 gaps
            if gap['filled']:
                continue
                
            # Bullish gap - look for price returning to fill gap (sell opportunity)
            if (gap['type'] == 'bullish' and 
                current_low <= gap['gap_high'] and 
                current_price > gap['gap_low']):
                
                return TradeSignal(
                    symbol=symbol,
                    action=OrderType.SELL,
                    price=current_price,
                    quantity=0,
                    strategy=StrategyType.FAIR_VALUE_GAP,
                    confidence=0.75,
                    timestamp=datetime.now()
                )
            
            # Bearish gap - look for price returning to fill gap (buy opportunity)
            elif (gap['type'] == 'bearish' and 
                  current_high >= gap['gap_low'] and 
                  current_price < gap['gap_high']):
                
                return TradeSignal(
                    symbol=symbol,
                    action=OrderType.BUY,
                    price=current_price,
                    quantity=0,
                    strategy=StrategyType.FAIR_VALUE_GAP,
                    confidence=0.75,
                    timestamp=datetime.now()
                )
        
        return None

class MACDStrategy(TradingStrategy):
    """MACD Strategy with signal line crossovers"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__("MACD_Strategy")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.required_candles = slow_period + signal_period + 5
    
    def calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = prices.ewm(span=self.fast_period).mean()
        ema_slow = prices.ewm(span=self.slow_period).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        if len(df) < self.required_candles:
            return None
        
        macd, signal, histogram = self.calculate_macd(df['close'])
        
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = signal.iloc[-2]
        current_price = df['close'].iloc[-1]
        
        # Bullish signal: MACD crosses above signal line
        if prev_macd <= prev_signal and current_macd > current_signal and current_macd < 0:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.BUY,
                price=current_price,
                quantity=0,
                strategy=StrategyType.MACD,
                confidence=0.7,
                timestamp=datetime.now()
            )
        
        # Bearish signal: MACD crosses below signal line
        elif prev_macd >= prev_signal and current_macd < current_signal and current_macd > 0:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.SELL,
                price=current_price,
                quantity=0,
                strategy=StrategyType.MACD,
                confidence=0.7,
                timestamp=datetime.now()
            )
        
        return None

class BollingerBandsStrategy(TradingStrategy):
    """Bollinger Bands Strategy"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("Bollinger_Bands")
        self.period = period
        self.std_dev = std_dev
        self.required_candles = period + 5
    
    def calculate_bollinger_bands(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=self.period).mean()
        std = prices.rolling(window=self.period).std()
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        return upper_band, sma, lower_band
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        if len(df) < self.required_candles:
            return None
        
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df['close'])
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        prev_upper = upper_band.iloc[-2]
        prev_lower = lower_band.iloc[-2]
        
        # Buy signal: Price bounces off lower band
        if prev_price <= prev_lower and current_price > current_lower:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.BUY,
                price=current_price,
                quantity=0,
                strategy=StrategyType.BOLLINGER_BANDS,
                confidence=0.65,
                timestamp=datetime.now()
            )
        
        # Sell signal: Price bounces off upper band
        elif prev_price >= prev_upper and current_price < current_upper:
            return TradeSignal(
                symbol=symbol,
                action=OrderType.SELL,
                price=current_price,
                quantity=0,
                strategy=StrategyType.BOLLINGER_BANDS,
                confidence=0.65,
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
        user_id = config.get('user_id', 'default_user')
        tier = config.get('tier', 'basic')
        self.risk_manager = RiskManager(user_id, tier)
        self.is_running = False
        self.trade_history = []

        # Load existing positions
        self.risk_manager.positions = load_positions(user_id)
    
    # Apply custom risk settings if provided
        if 'risk_settings' in config:
            self.risk_manager.update_risk_settings(config['risk_settings'])
    
        
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
    """Execute a trading signal with enhanced risk management"""
    if exchange_name not in self.exchanges:
        logger.error(f"Exchange {exchange_name} not available")
        return
    
    exchange = self.exchanges[exchange_name]
    
    # Get current balance
    balance = exchange.get_balance()
    if not balance:
        logger.error("Could not fetch balance")
        return
    
    # Calculate total portfolio value
    total_balance = balance.get('total', {}).get('USDT', 0) or balance.get('total', {}).get('USD', 0)
    if total_balance <= 0:
        logger.error("Insufficient balance")
        return
    
    # Enhanced risk management checks
    can_trade, reason = self.risk_manager.can_open_new_position(total_balance)
    if not can_trade:
        logger.warning(f"Trade blocked by risk management: {reason}")
        return
    
    # Get risk settings
    settings = self.risk_manager.get_effective_settings()
    
    # Calculate stop loss and take profit prices
    if signal.action.value == 'buy':
        stop_loss_price = signal.price * (1 - settings['default_stop_loss']/100)
        take_profit_price = signal.price * (1 + settings['default_take_profit']/100)
    else:
        stop_loss_price = signal.price * (1 + settings['default_stop_loss']/100)
        take_profit_price = signal.price * (1 - settings['default_take_profit']/100)
    
    # Calculate enhanced position size
    position_size = self.risk_manager.calculate_position_size(
        signal.price, 
        total_balance, 
        stop_loss_price
    )
    
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
            # Create position object for tracking
            position = Position(
                symbol=signal.symbol,
                side=signal.action.value,
                size=position_size,
                entry_price=signal.price,
                current_price=signal.price,
                entry_time=datetime.now(),
                stop_loss=stop_loss_price,
                take_profit=take_profit_price,
                exchange=exchange_name
            )
            
            # Add to risk manager
            self.risk_manager.add_position(position)
            
            # Save positions
            save_positions(self.risk_manager.user_id, self.risk_manager.positions)
            
            # Record trade (enhanced)
            trade_record = {
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'action': signal.action.value,
                'price': signal.price,
                'quantity': position_size,
                'strategy': signal.strategy.value,
                'order_id': order.get('id'),
                'position_id': position.position_id,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'risk_settings': settings
            }
            self.trade_history.append(trade_record)
            logger.info(f"Enhanced trade executed: {trade_record}")
            
    except Exception as e:
        logger.error(f"Failed to execute trade: {e}")

    def update_positions(self):
    """Update current prices for all open positions"""
    try:
        for position in self.risk_manager.get_open_positions():
            # Get current price from exchange
            exchange = self.exchanges.get(position.exchange)
            if exchange:
                current_data = exchange.get_candles(position.symbol, limit=1)
                if not current_data.empty:
                    current_price = current_data['close'].iloc[-1]
                    
                    # Update position
                    self.risk_manager.update_position_price(position.position_id, current_price)
                    
                    # Check for stop loss or take profit
                    if position.side == 'buy':
                        if current_price <= position.stop_loss or current_price >= position.take_profit:
                            self.close_position(position, current_price)
                    else:
                        if current_price >= position.stop_loss or current_price <= position.take_profit:
                            self.close_position(position, current_price)
        
        # Save updated positions
        save_positions(self.risk_manager.user_id, self.risk_manager.positions)
        
    except Exception as e:
        logger.error(f"Error updating positions: {e}")

    def close_position(self, position: Position, close_price: float):
        """Close a position"""
        try:
            exchange = self.exchanges.get(position.exchange)
            if exchange:
                # Execute close order
                close_action = 'sell' if position.side == 'buy' else 'buy'
                order = exchange.place_order(position.symbol, close_action, position.size)
            
                if order:
                    # Update position status
                    self.risk_manager.close_position(position.position_id, close_price)
                
                    logger.info(f"Position closed: {position.symbol} P&L: ${position.realized_pnl:.2f}")
                
                    # Record close trade
                    close_record = {
                        'timestamp': datetime.now(),
                        'symbol': position.symbol,
                        'action': 'close_' + position.side,
                        'price': close_price,
                        'quantity': position.size,
                        'strategy': 'risk_management',
                        'order_id': order.get('id'),
                        'position_id': position.position_id,
                        'pnl': position.realized_pnl
                    }
                    self.trade_history.append(close_record)
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")

    def run_analysis_cycle(self):
        """Run one analysis cycle for all symbols"""
        # Update existing positions first
        self.update_positions()

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

        # Get position statistics
        open_positions = self.risk_manager.get_open_positions()
        total_unrealized_pnl = self.risk_manager.get_total_unrealized_pnl()
    
        # Calculate realized P&L from closed positions
        closed_trades = [t for t in self.trade_history if 'pnl' in t]
        total_realized_pnl = sum(t['pnl'] for t in closed_trades)
        
        stats = {
            'total_trades': len(df),
            'buy_trades': len(df[df['action'] == 'buy']),
            'sell_trades': len(df[df['action'] == 'sell']),
            'strategies_used': df['strategy'].unique().tolist(),
            'symbols_traded': df['symbol'].unique().tolist(),
            'trading_period': {
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max()
            },
            'positions': {
                'open_positions': len(open_positions),
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'total_pnl': total_unrealized_pnl + total_realized_pnl
            },
            'risk_metrics': self.risk_manager.get_effective_settings()
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