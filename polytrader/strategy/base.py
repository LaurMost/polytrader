"""
Base strategy class for Polytrader.

Provides a framework for implementing trading strategies with lifecycle hooks.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from polytrader.config import get_config
from polytrader.core.client import PolymarketClient
from polytrader.data.models import (
    Market,
    Order,
    OrderSide,
    OrderType,
    Position,
    PriceUpdate,
    Trade,
)
from polytrader.utils.logging import get_logger, trade_logger


class Strategy(ABC):
    """
    Base class for trading strategies.
    
    Subclass this to implement your own trading logic.
    
    Example:
        class MyStrategy(Strategy):
            name = "my_strategy"
            markets = ["https://polymarket.com/event/..."]
            
            def on_price_update(self, market: Market, price: float):
                if price < 0.3 and self.position(market) == 0:
                    self.buy(market, size=100)
            
            def on_fill(self, order: Order, trade: Trade):
                self.log(f"Order filled: {trade}")
    """

    # Strategy metadata (override in subclass)
    name: str = "base_strategy"
    description: str = ""
    version: str = "1.0.0"
    
    # Markets to trade (URLs or market IDs)
    markets: list[str] = []

    def __init__(self):
        """Initialize the strategy."""
        self.config = get_config()
        self.client = PolymarketClient()
        self.logger = get_logger(f"strategy.{self.name}")
        
        # State
        self._markets: dict[str, Market] = {}
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, Order] = {}
        self._trades: list[Trade] = []
        
        # Runtime state
        self._running = False
        self._executor = None  # Set by runner
        
        # Statistics
        self._stats = {
            "start_time": None,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
        }

    # ==================== Lifecycle Hooks ====================

    def on_start(self) -> None:
        """
        Called when the strategy starts.
        
        Override to perform initialization logic.
        """
        pass

    def on_stop(self) -> None:
        """
        Called when the strategy stops.
        
        Override to perform cleanup logic.
        """
        pass

    @abstractmethod
    def on_price_update(self, market: Market, price: float) -> None:
        """
        Called when a price update is received.
        
        This is the main hook for implementing trading logic.
        
        Args:
            market: Market object with updated prices
            price: Current YES price
        """
        pass

    def on_orderbook_update(self, market: Market, orderbook: dict) -> None:
        """
        Called when orderbook data is updated.
        
        Args:
            market: Market object
            orderbook: Orderbook data with bids/asks
        """
        pass

    def on_order_created(self, order: Order) -> None:
        """
        Called when an order is created.
        
        Args:
            order: The created order
        """
        pass

    def on_fill(self, order: Order, trade: Trade) -> None:
        """
        Called when an order is filled.
        
        Args:
            order: The filled order
            trade: The resulting trade
        """
        pass

    def on_order_cancelled(self, order: Order) -> None:
        """
        Called when an order is cancelled.
        
        Args:
            order: The cancelled order
        """
        pass

    def on_position_opened(self, position: Position) -> None:
        """
        Called when a new position is opened.
        
        Args:
            position: The new position
        """
        pass

    def on_position_closed(self, position: Position, pnl: float) -> None:
        """
        Called when a position is closed.
        
        Args:
            position: The closed position
            pnl: Realized P&L
        """
        pass

    def on_error(self, error: Exception) -> None:
        """
        Called when an error occurs.
        
        Args:
            error: The exception that occurred
        """
        self.logger.error(f"Strategy error: {error}")

    # ==================== Trading Methods ====================

    def buy(
        self,
        market: Market,
        size: Optional[float] = None,
        price: Optional[float] = None,
        outcome: str = "YES",
    ) -> Optional[Order]:
        """
        Place a buy order.
        
        Args:
            market: Market to trade
            size: Order size in USDC (default from config)
            price: Limit price (default: market price)
            outcome: "YES" or "NO"
            
        Returns:
            Order object if successful
        """
        size = size or self.config.get("strategy.default_size", 100.0)
        
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        current_price = market.price_yes if outcome == "YES" else market.price_no
        price = price or current_price
        
        order = self._create_order(
            market=market,
            token_id=token_id,
            side=OrderSide.BUY,
            price=price,
            size=size,
        )
        
        if order:
            trade_logger.log_order_created(
                order.id, market.id, "BUY", price, size
            )
            self.on_order_created(order)
        
        return order

    def sell(
        self,
        market: Market,
        size: Optional[float] = None,
        price: Optional[float] = None,
        outcome: str = "YES",
    ) -> Optional[Order]:
        """
        Place a sell order.
        
        Args:
            market: Market to trade
            size: Order size (default: current position)
            price: Limit price (default: market price)
            outcome: "YES" or "NO"
            
        Returns:
            Order object if successful
        """
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        current_price = market.price_yes if outcome == "YES" else market.price_no
        
        # Default to closing current position
        if size is None:
            pos = self._positions.get(token_id)
            size = pos.size if pos else 0
        
        if size <= 0:
            self.logger.warning("No position to sell")
            return None
        
        price = price or current_price
        
        order = self._create_order(
            market=market,
            token_id=token_id,
            side=OrderSide.SELL,
            price=price,
            size=size,
        )
        
        if order:
            trade_logger.log_order_created(
                order.id, market.id, "SELL", price, size
            )
            self.on_order_created(order)
        
        return order

    def cancel_order(self, order: Order) -> bool:
        """
        Cancel an open order.
        
        Args:
            order: Order to cancel
            
        Returns:
            True if cancelled successfully
        """
        if self._executor:
            success = self._executor.cancel_order(order)
            if success:
                trade_logger.log_order_cancelled(order.id)
                self.on_order_cancelled(order)
            return success
        return False

    def cancel_all_orders(self, market: Optional[Market] = None) -> int:
        """
        Cancel all open orders.
        
        Args:
            market: Optionally filter by market
            
        Returns:
            Number of orders cancelled
        """
        cancelled = 0
        for order in list(self._orders.values()):
            if order.is_open:
                if market is None or order.market_id == market.id:
                    if self.cancel_order(order):
                        cancelled += 1
        return cancelled

    def _create_order(
        self,
        market: Market,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
    ) -> Optional[Order]:
        """Create an order through the executor."""
        if self._executor:
            order = self._executor.create_order(
                market_id=market.id,
                token_id=token_id,
                side=side,
                price=price,
                size=size,
            )
            if order:
                self._orders[order.id] = order
            return order
        
        # Fallback to client
        return self.client.create_order(
            token_id=token_id,
            side=side,
            price=price,
            size=size,
        )

    # ==================== Position Methods ====================

    def position(self, market: Market, outcome: str = "YES") -> float:
        """
        Get current position size in a market.
        
        Args:
            market: Market to check
            outcome: "YES" or "NO"
            
        Returns:
            Position size (0 if no position)
        """
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        pos = self._positions.get(token_id)
        return pos.size if pos else 0.0

    def has_position(self, market: Market) -> bool:
        """Check if we have any position in a market."""
        return (
            self.position(market, "YES") != 0 or
            self.position(market, "NO") != 0
        )

    def get_position(self, market: Market, outcome: str = "YES") -> Optional[Position]:
        """Get position object for a market."""
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        return self._positions.get(token_id)

    def all_positions(self) -> list[Position]:
        """Get all open positions."""
        return [p for p in self._positions.values() if not p.is_flat]

    # ==================== Market Methods ====================

    def get_market(self, market_id: str) -> Optional[Market]:
        """Get a market by ID."""
        return self._markets.get(market_id)

    def all_markets(self) -> list[Market]:
        """Get all tracked markets."""
        return list(self._markets.values())

    def refresh_market(self, market: Market) -> Market:
        """Refresh market data from API."""
        updated = self.client.get_market_by_id(market.id)
        if updated:
            self._markets[market.id] = updated
            return updated
        return market

    # ==================== Utility Methods ====================

    def log(self, message: str, level: str = "info") -> None:
        """
        Log a message.
        
        Args:
            message: Message to log
            level: Log level (debug, info, warning, error)
        """
        log_func = getattr(self.logger, level, self.logger.info)
        log_func(f"[{self.name}] {message}")

    def signal(self, market: Market, signal: str, reason: str = "") -> None:
        """
        Log a trading signal.
        
        Args:
            market: Market the signal is for
            signal: Signal type (e.g., "BUY", "SELL", "HOLD")
            reason: Reason for the signal
        """
        trade_logger.log_strategy_signal(self.name, market.id, signal, reason)

    @property
    def balance(self) -> float:
        """Get current account balance."""
        if self._executor:
            return self._executor.balance
        return self.client.get_balance()

    @property
    def equity(self) -> float:
        """Get total account equity (balance + position value)."""
        position_value = sum(
            p.size * self._get_current_price(p.token_id)
            for p in self._positions.values()
        )
        return self.balance + position_value

    def _get_current_price(self, token_id: str) -> float:
        """Get current price for a token."""
        for market in self._markets.values():
            if market.token_id_yes == token_id:
                return market.price_yes
            if market.token_id_no == token_id:
                return market.price_no
        return 0.0

    @property
    def pnl(self) -> float:
        """Get total realized P&L."""
        return self._stats["total_pnl"]

    @property
    def stats(self) -> dict[str, Any]:
        """Get strategy statistics."""
        return self._stats.copy()

    def __repr__(self) -> str:
        return f"Strategy(name={self.name}, markets={len(self._markets)})"

