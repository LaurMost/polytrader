"""
Data models for Polytrader.

Defines the core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    """Order side (buy/sell)."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    """Order type."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"


@dataclass
class Market:
    """Represents a Polymarket prediction market."""
    
    # Core identifiers
    id: str
    condition_id: str
    question: str
    slug: str
    
    # Token IDs for YES/NO outcomes
    token_id_yes: str
    token_id_no: str
    
    # Current market state
    price_yes: float = 0.0
    price_no: float = 0.0
    volume: float = 0.0
    liquidity: float = 0.0
    
    # Market metadata
    description: str = ""
    category: str = ""
    end_date: Optional[datetime] = None
    resolution_source: str = ""
    
    # Status
    active: bool = True
    closed: bool = False
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def url(self) -> str:
        """Get Polymarket URL for this market."""
        return f"https://polymarket.com/event/{self.slug}"
    
    @property
    def implied_probability_yes(self) -> float:
        """Get implied probability of YES outcome."""
        return self.price_yes
    
    @property
    def implied_probability_no(self) -> float:
        """Get implied probability of NO outcome."""
        return self.price_no
    
    def __repr__(self) -> str:
        return f"Market(id={self.id}, question='{self.question[:50]}...', yes={self.price_yes:.2f})"


@dataclass
class Order:
    """Represents a trading order."""
    
    id: str
    market_id: str
    token_id: str
    
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    
    price: float
    size: float
    filled_size: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Paper trading flag
    is_paper: bool = False
    
    @property
    def remaining_size(self) -> float:
        """Get unfilled order size."""
        return self.size - self.filled_size
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_open(self) -> bool:
        """Check if order is open."""
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)
    
    @property
    def fill_percentage(self) -> float:
        """Get percentage of order filled."""
        if self.size == 0:
            return 0.0
        return (self.filled_size / self.size) * 100
    
    def __repr__(self) -> str:
        return f"Order(id={self.id}, {self.side.value} {self.size}@{self.price}, status={self.status.value})"


@dataclass
class Trade:
    """Represents an executed trade."""
    
    id: str
    order_id: str
    market_id: str
    token_id: str
    
    side: OrderSide
    price: float
    size: float
    
    # Fees
    fee: float = 0.0
    
    # Timestamps
    executed_at: datetime = field(default_factory=datetime.now)
    
    # Paper trading flag
    is_paper: bool = False
    
    @property
    def value(self) -> float:
        """Get trade value (price * size)."""
        return self.price * self.size
    
    @property
    def net_value(self) -> float:
        """Get net trade value after fees."""
        if self.side == OrderSide.BUY:
            return self.value + self.fee
        return self.value - self.fee
    
    def __repr__(self) -> str:
        return f"Trade(id={self.id}, {self.side.value} {self.size}@{self.price})"


@dataclass
class Position:
    """Represents a position in a market."""
    
    market_id: str
    token_id: str
    
    # Position details
    size: float = 0.0
    avg_entry_price: float = 0.0
    
    # P&L tracking
    realized_pnl: float = 0.0
    
    # Timestamps
    opened_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.size > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.size < 0
    
    @property
    def is_flat(self) -> bool:
        """Check if position is flat (no position)."""
        return self.size == 0
    
    @property
    def cost_basis(self) -> float:
        """Get total cost basis of position."""
        return abs(self.size) * self.avg_entry_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L at current price."""
        if self.is_flat:
            return 0.0
        return (current_price - self.avg_entry_price) * self.size
    
    def total_pnl(self, current_price: float) -> float:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl(current_price)
    
    def __repr__(self) -> str:
        return f"Position(market={self.market_id}, size={self.size}, avg_price={self.avg_entry_price:.4f})"


@dataclass
class PriceUpdate:
    """Represents a real-time price update from WebSocket."""
    
    market_id: str
    token_id: str
    
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional orderbook data
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    
    @property
    def spread(self) -> Optional[float]:
        """Calculate bid-ask spread."""
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None
    
    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price."""
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None


@dataclass
class AccountBalance:
    """Represents account balance information."""
    
    usdc_balance: float = 0.0
    total_position_value: float = 0.0
    unrealized_pnl: float = 0.0
    
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_equity(self) -> float:
        """Get total account equity."""
        return self.usdc_balance + self.total_position_value
    
    def __repr__(self) -> str:
        return f"AccountBalance(usdc={self.usdc_balance:.2f}, equity={self.total_equity:.2f})"

