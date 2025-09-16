import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json

class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"

@dataclass
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
    realized_pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    position_id: str = ""
    exchange: str = ""
    entry_value: float = 0.0
    current_value: float = 0.0
    
    def __post_init__(self):
        if not self.position_id:
            self.position_id = f"{self.symbol}_{self.side}_{int(self.entry_time.timestamp())}"
        self.entry_value = self.size * self.entry_price
        self.update_current_price(self.current_price)
    
    def update_current_price(self, price: float):
        self.current_price = price
        self.current_value = self.size * price
        
        if self.side == 'buy':
            self.unrealized_pnl = (price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.size
    
    def get_pnl_percentage(self) -> float:
        """Get PnL as percentage of entry value"""
        if self.entry_value == 0:
            return 0.0
        return (self.unrealized_pnl / self.entry_value) * 100
    
    def to_dict(self) -> dict:
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'entry_time': self.entry_time.isoformat(),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'status': self.status.value,
            'exchange': self.exchange,
            'entry_value': self.entry_value,
            'current_value': self.current_value,
            'pnl_percentage': self.get_pnl_percentage()
        }

class RiskManager:
    """Enhanced risk management with comprehensive position tracking"""
    
    def __init__(self, user_id: str, tier: str = 'basic'):
        self.user_id = user_id
        self.tier = tier
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.risk_settings = self.get_tier_risk_settings(tier)
        self.custom_settings = {}
        
    def get_tier_risk_settings(self, tier: str) -> dict:
        """Get default risk settings based on subscription tier"""
        tier_settings = {
            'basic': {
                'max_position_size': 5.0,      # 5% max per trade
                'max_daily_loss': 3.0,         # 3% max daily loss
                'default_stop_loss': 3.0,      # 3% stop loss
                'default_take_profit': 6.0,    # 6% take profit
                'max_open_positions': 3,
                'max_daily_trades': 10
            },
            'pro': {
                'max_position_size': 8.0,      # 8% max per trade
                'max_daily_loss': 5.0,         # 5% max daily loss
                'default_stop_loss': 2.5,      # 2.5% stop loss
                'default_take_profit': 5.0,    # 5% take profit
                'max_open_positions': 5,
                'max_daily_trades': 25
            },
            'premium': {
                'max_position_size': 10.0,     # 10% max per trade
                'max_daily_loss': 7.0,         # 7% max daily loss
                'default_stop_loss': 2.0,      # 2% stop loss
                'default_take_profit': 4.0,    # 4% take profit
                'max_open_positions': 8,
                'max_daily_trades': 50
            },
            'enterprise': {
                'max_position_size': 15.0,     # 15% max per trade
                'max_daily_loss': 10.0,        # 10% max daily loss
                'default_stop_loss': 1.5,      # 1.5% stop loss
                'default_take_profit': 3.0,    # 3% take profit
                'max_open_positions': 12,
                'max_daily_trades': 100
            }
        }
        return tier_settings.get(tier, tier_settings['basic'])
    
    def update_risk_settings(self, settings: dict):
        """Update custom risk settings"""
        self.custom_settings.update(settings)
    
    def get_effective_settings(self) -> dict:
        """Get effective risk settings (custom overrides tier defaults)"""
        effective = self.risk_settings.copy()
        effective.update(self.custom_settings)
        return effective
    
    def add_position(self, position: Position):
        """Add a new position to tracking"""
        self.positions[position.position_id] = position
        self.daily_trade_count += 1
    
    def update_position_price(self, position_id: str, current_price: float):
        """Update current price for a position"""
        if position_id in self.positions:
            self.positions[position_id].update_current_price(current_price)
    
    def close_position(self, position_id: str, close_price: float, close_time: datetime = None):
        """Close a position and calculate realized PnL"""
        if position_id in self.positions:
            position = self.positions[position_id]
            position.current_price = close_price
            position.update_current_price(close_price)
            position.realized_pnl = position.unrealized_pnl
            position.status = PositionStatus.CLOSED
            
            self.daily_pnl += position.realized_pnl
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
    
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized PnL across all open positions"""
        return sum(pos.unrealized_pnl for pos in self.get_open_positions())
    
    def can_open_new_position(self, portfolio_value: float) -> Tuple[bool, str]:
        """Check if a new position can be opened based on risk rules"""
        settings = self.get_effective_settings()
        
        # Check max open positions
        open_count = len(self.get_open_positions())
        if open_count >= settings['max_open_positions']:
            return False, f"Maximum open positions reached ({open_count}/{settings['max_open_positions']})"
        
        # Check daily loss limit
        daily_loss_pct = (self.daily_pnl / portfolio_value) * 100 if portfolio_value > 0 else 0
        if daily_loss_pct <= -settings['max_daily_loss']:
            return False, f"Daily loss limit reached ({daily_loss_pct:.2f}%/{settings['max_daily_loss']}%)"
        
        # Check daily trade limit
        if self.daily_trade_count >= settings['max_daily_trades']:
            return False, f"Daily trade limit reached ({self.daily_trade_count}/{settings['max_daily_trades']})"
        
        return True, "OK"
    
    def calculate_position_size(self, entry_price: float, portfolio_value: float, stop_loss_price: float = None) -> float:
        """Calculate optimal position size based on risk settings"""
        settings = self.get_effective_settings()
        
        # Calculate position size based on max position percentage
        max_position_value = portfolio_value * (settings['max_position_size'] / 100)
        position_size = max_position_value / entry_price
        
        # If stop loss is provided, adjust size based on risk per share
        if stop_loss_price and stop_loss_price > 0:
            risk_per_share = abs(entry_price - stop_loss_price)
            max_risk_amount = portfolio_value * (settings['default_stop_loss'] / 100)
            risk_based_size = max_risk_amount / risk_per_share
            position_size = min(position_size, risk_based_size)
        
        return position_size

class FairValueGapStrategy:
    """Fair Value Gap Strategy - Identifies imbalances in price action"""
    
    def __init__(self, lookback_period: int = 20, min_gap_size: float = 0.002, gap_fill_threshold: float = 0.5):
        self.name = "Fair_Value_Gap"
        self.lookback_period = lookback_period
        self.min_gap_size = min_gap_size  # Minimum gap size as percentage
        self.gap_fill_threshold = gap_fill_threshold  # How much of gap needs to be filled
        self.required_candles = lookback_period + 5
        self.active_gaps = []
    
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Identify fair value gaps in the price data"""
        gaps = []
        
        if len(df) < 3:
            return gaps
            
        for i in range(2, len(df)):
            current = df.iloc[i]
            prev1 = df.iloc[i-1]
            prev2 = df.iloc[i-2]
            
            # Check for bullish gap (gap up)
            if (prev1['low'] > prev2['high'] and current['low'] > prev2['high']):
                gap_size = (prev1['low'] - prev2['high']) / prev2['close']
                if gap_size >= self.min_gap_size:
                    gaps.append({
                        'type': 'bullish',
                        'gap_low': prev2['high'],
                        'gap_high': prev1['low'],
                        'gap_size': gap_size,
                        'index': i,
                        'timestamp': current.name,
                        'filled': False
                    })
            
            # Check for bearish gap (gap down)
            elif (prev1['high'] < prev2['low'] and current['high'] < prev2['low']):
                gap_size = (prev2['low'] - prev1['high']) / prev2['close']
                if gap_size >= self.min_gap_size:
                    gaps.append({
                        'type': 'bearish',
                        'gap_low': prev1['high'],
                        'gap_high': prev2['low'],
                        'gap_size': gap_size,
                        'index': i,
                        'timestamp': current.name,
                        'filled': False
                    })
        
        return gaps
    
    def check_gap_fills(self, df: pd.DataFrame, gaps: List[Dict]) -> List[Dict]:
        """Check if any gaps have been filled"""
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        for gap in gaps:
            if gap['filled']:
                continue
                
            if gap['type'] == 'bullish':
                # Check if price has moved back down to fill the gap
                if current_low <= gap['gap_low'] + (gap['gap_high'] - gap['gap_low']) * self.gap_fill_threshold:
                    gap['filled'] = True
                    gap['fill_price'] = current_price
                    
            elif gap['type'] == 'bearish':
                # Check if price has moved back up to fill the gap
                if current_high >= gap['gap_high'] - (gap['gap_high'] - gap['gap_low']) * self.gap_fill_threshold:
                    gap['filled'] = True
                    gap['fill_price'] = current_price
        
        return gaps
    
    def generate_signals(self, df: pd.DataFrame) -> Dict:
        """Generate trading signals based on fair value gaps"""
        if len(df) < self.required_candles:
            return {'action': 'hold', 'confidence': 0, 'reason': 'insufficient_data'}
        
        # Identify new gaps
        recent_gaps = self.identify_fair_value_gaps(df.tail(self.lookback_period))
        
        # Update active gaps
        self.active_gaps.extend(recent_gaps)
        self.active_gaps = self.check_gap_fills(df, self.active_gaps)
        
        # Remove old filled gaps (keep only recent unfilled ones)
        current_time = df.index[-1]
        cutoff_time = current_time - timedelta(days=7)  # Keep gaps for 7 days
        self.active_gaps = [gap for gap in self.active_gaps 
                           if not gap['filled'] and gap['timestamp'] > cutoff_time]
        
        current_price = df['close'].iloc[-1]
        
        # Look for trading opportunities
        for gap in self.active_gaps:
            if gap['filled']:
                continue
                
            gap_center = (gap['gap_high'] + gap['gap_low']) / 2
            distance_to_gap = abs(current_price - gap_center) / current_price
            
            # Signal strength based on gap size and proximity
            confidence = min(90, gap['gap_size'] * 10000)  # Scale gap size to confidence
            
            if gap['type'] == 'bullish' and distance_to_gap < 0.01:  # Within 1% of gap
                # Price near unfilled bullish gap - expect move up to fill it
                return {
                    'action': 'buy',
                    'confidence': confidence,
                    'reason': f'Price near unfilled bullish FVG at {gap_center:.4f}',
                    'target': gap['gap_high'],
                    'stop_loss': gap['gap_low'] * 0.995,  # Just below gap low
                    'gap_info': gap
                }
                
            elif gap['type'] == 'bearish' and distance_to_gap < 0.01:  # Within 1% of gap
                # Price near unfilled bearish gap - expect move down to fill it
                return {
                    'action': 'sell',
                    'confidence': confidence,
                    'reason': f'Price near unfilled bearish FVG at {gap_center:.4f}',
                    'target': gap['gap_low'],
                    'stop_loss': gap['gap_high'] * 1.005,  # Just above gap high
                    'gap_info': gap
                }
        
        return {'action': 'hold', 'confidence': 0, 'reason': 'no_gap_opportunities'}

# Extended coin list for different tiers
TIER_COINS = {
    'basic': [
        'BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD'
    ],
    'pro': [
        'BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD',
        'MATIC-USD', 'SOL-USD', 'AVAX-USD', 'ALGO-USD', 'XTZ-USD',
        'ATOM-USD', 'LUNA-USD', 'NEAR-USD', 'FTM-USD', 'ONE-USD'
    ],
    'premium': [
        'BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD',
        'MATIC-USD', 'SOL-USD', 'AVAX-USD', 'ALGO-USD', 'XTZ-USD',
        'ATOM-USD', 'LUNA-USD', 'NEAR-USD', 'FTM-USD', 'ONE-USD',
        'UNI-USD', 'AAVE-USD', 'COMP-USD', 'MKR-USD', 'SNX-USD',
        'CRV-USD', 'YFI-USD', 'SUSHI-USD', '1INCH-USD', 'BAL-USD',
        'DOGE-USD', 'SHIB-USD', 'LTC-USD', 'BCH-USD', 'XLM-USD'
    ],
    'enterprise': [
        # All premium coins plus additional altcoins
        'BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD',
        'MATIC-USD', 'SOL-USD', 'AVAX-USD', 'ALGO-USD', 'XTZ-USD',
        'ATOM-USD', 'LUNA-USD', 'NEAR-USD', 'FTM-USD', 'ONE-USD',
        'UNI-USD', 'AAVE-USD', 'COMP-USD', 'MKR-USD', 'SNX-USD',
        'CRV-USD', 'YFI-USD', 'SUSHI-USD', '1INCH-USD', 'BAL-USD',
        'DOGE-USD', 'SHIB-USD', 'LTC-USD', 'BCH-USD', 'XLM-USD',
        'LRC-USD', 'IMX-USD', 'OMG-USD', 'BAND-USD', 'API3-USD',
        'TRB-USD', 'REQ-USD', 'FLOW-USD', 'EGLD-USD', 'SAND-USD',
        'MANA-USD', 'AXS-USD', 'ENJ-USD', 'CHZ-USD', 'BAT-USD'
    ]
}

def get_available_coins(tier: str) -> List[str]:
    """Get available coins based on subscription tier"""
    return TIER_COINS.get(tier, TIER_COINS['basic'])

# Enhanced position tracking functions
def save_positions(user_id: str, positions: Dict[str, Position]):
    """Save positions to persistent storage"""
    positions_data = {pid: pos.to_dict() for pid, pos in positions.items()}
    
    # Save to file (in production, use database)
    filename = f"user_data/{user_id}_positions.json"
    os.makedirs("user_data", exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(positions_data, f, indent=2)

def load_positions(user_id: str) -> Dict[str, Position]:
    """Load positions from persistent storage"""
    filename = f"user_data/{user_id}_positions.json"
    
    if not os.path.exists(filename):
        return {}
    
    try:
        with open(filename, 'r') as f:
            positions_data = json.load(f)
        
        positions = {}
        for pid, data in positions_data.items():
            pos = Position(
                symbol=data['symbol'],
                side=data['side'],
                size=data['size'],
                entry_price=data['entry_price'],
                current_price=data['current_price'],
                entry_time=datetime.fromisoformat(data['entry_time']),
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                unrealized_pnl=data.get('unrealized_pnl', 0),
                realized_pnl=data.get('realized_pnl', 0),
                position_id=data.get('position_id', pid)
            )
            pos.status = PositionStatus(data.get('status', 'open'))
            pos.exchange = data.get('exchange', '')
            positions[pid] = pos
            
        return positions
        
    except Exception as e:
        print(f"Error loading positions: {e}")
        return {}