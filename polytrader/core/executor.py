"""
Order executor for Polytrader.

Handles order execution in both paper and live trading modes.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from polytrader.config import get_config
from polytrader.core.client import PolymarketClient
from polytrader.data.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Trade,
)
from polytrader.utils.logging import get_logger, trade_logger

logger = get_logger(__name__)


class OrderExecutor:
    """
    Executes orders in paper or live mode.
    
    Paper mode simulates order execution with configurable slippage and delays.
    Live mode uses the Polymarket CLOB API.
    
    Usage:
        executor = OrderExecutor()
        
        order = executor.create_order(
            market_id="...",
            token_id="...",
            side=OrderSide.BUY,
            price=0.5,
            size=100
        )
    """

    def __init__(self):
        """Initialize the executor."""
        self.config = get_config()
        self.client = PolymarketClient()
        
        # Paper trading state
        self._balance: float = self.config.get("paper.starting_balance", 10000.0)
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self._trades: list[Trade] = []
        
        # Paper trading settings
        self._slippage = self.config.get("paper.slippage", 0.001)
        self._fill_delay = self.config.get("paper.fill_delay", 0.5)

    # ==================== Order Management ====================

    def create_order(
        self,
        market_id: str,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
    ) -> Optional[Order]:
        """
        Create and execute an order.
        
        Args:
            market_id: Market ID
            token_id: Token ID to trade
            side: BUY or SELL
            price: Limit price
            size: Order size in USDC
            order_type: LIMIT or MARKET
            
        Returns:
            Order object if successful
        """
        # Validate
        if size <= 0:
            logger.error("Order size must be positive")
            return None
        
        if price <= 0 or price >= 1:
            logger.error("Price must be between 0 and 1")
            return None
        
        # Check balance for buys
        if side == OrderSide.BUY:
            cost = price * size
            if cost > self._balance:
                logger.error(f"Insufficient balance: {self._balance:.2f} < {cost:.2f}")
                return None
        
        # Check position for sells
        if side == OrderSide.SELL:
            pos = self._positions.get(token_id)
            if not pos or pos.size < size:
                logger.error("Insufficient position to sell")
                return None
        
        if self.config.is_paper:
            return self._execute_paper_order(
                market_id, token_id, side, price, size, order_type
            )
        else:
            return self._execute_live_order(
                market_id, token_id, side, price, size, order_type
            )

    def _execute_paper_order(
        self,
        market_id: str,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
        order_type: OrderType,
    ) -> Order:
        """Execute a paper (simulated) order."""
        order_id = f"paper_{uuid.uuid4().hex[:12]}"
        
        # Apply slippage
        if order_type == OrderType.MARKET:
            if side == OrderSide.BUY:
                fill_price = price * (1 + self._slippage)
            else:
                fill_price = price * (1 - self._slippage)
        else:
            fill_price = price
        
        # Create order
        order = Order(
            id=order_id,
            market_id=market_id,
            token_id=token_id,
            side=side,
            order_type=order_type,
            status=OrderStatus.FILLED,  # Paper orders fill immediately
            price=price,
            size=size,
            filled_size=size,
            filled_at=datetime.now(),
            is_paper=True,
        )
        
        self._orders[order_id] = order
        
        # Create trade
        trade = self._create_trade(order, fill_price, size)
        
        # Update balance and position
        self._update_balance(side, fill_price, size)
        self._update_position(token_id, side, fill_price, size)
        
        logger.info(
            f"Paper order executed: {side.value} {size}@{fill_price:.4f} "
            f"(balance: ${self._balance:.2f})"
        )
        
        return order

    def _execute_live_order(
        self,
        market_id: str,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
        order_type: OrderType,
    ) -> Optional[Order]:
        """Execute a live order via the CLOB API."""
        order = self.client.create_order(
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            order_type=order_type,
        )
        
        if order:
            order.market_id = market_id
            self._orders[order.id] = order
            logger.info(f"Live order created: {order}")
        
        return order

    def cancel_order(self, order: Order) -> bool:
        """
        Cancel an open order.
        
        Args:
            order: Order to cancel
            
        Returns:
            True if cancelled successfully
        """
        if order.status not in (OrderStatus.OPEN, OrderStatus.PENDING):
            logger.warning(f"Cannot cancel order with status: {order.status}")
            return False
        
        if self.config.is_paper:
            order.status = OrderStatus.CANCELLED
            logger.info(f"Paper order cancelled: {order.id}")
            return True
        else:
            success = self.client.cancel_order(order.id)
            if success:
                order.status = OrderStatus.CANCELLED
            return success

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        return self._orders.get(order_id)

    def get_open_orders(self) -> list[Order]:
        """Get all open orders."""
        return [o for o in self._orders.values() if o.is_open]

    # ==================== Position Management ====================

    def get_position(self, token_id: str) -> Optional[Position]:
        """Get position for a token."""
        return self._positions.get(token_id)

    def get_all_positions(self) -> list[Position]:
        """Get all positions."""
        return list(self._positions.values())

    def _update_position(
        self,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
    ) -> None:
        """Update position after a trade."""
        pos = self._positions.get(token_id)
        
        if pos is None:
            pos = Position(
                market_id="",
                token_id=token_id,
                opened_at=datetime.now(),
            )
            self._positions[token_id] = pos
        
        if side == OrderSide.BUY:
            # Add to position
            total_cost = pos.size * pos.avg_entry_price + size * price
            pos.size += size
            if pos.size > 0:
                pos.avg_entry_price = total_cost / pos.size
        else:
            # Reduce position
            if pos.size > 0:
                # Calculate realized P&L
                pnl = (price - pos.avg_entry_price) * size
                pos.realized_pnl += pnl
            pos.size -= size
        
        pos.updated_at = datetime.now()
        
        # Remove flat positions
        if pos.is_flat:
            del self._positions[token_id]

    # ==================== Trade Management ====================

    def _create_trade(self, order: Order, price: float, size: float) -> Trade:
        """Create a trade record."""
        trade = Trade(
            id=f"trade_{uuid.uuid4().hex[:12]}",
            order_id=order.id,
            market_id=order.market_id,
            token_id=order.token_id,
            side=order.side,
            price=price,
            size=size,
            is_paper=order.is_paper,
        )
        
        self._trades.append(trade)
        return trade

    def get_trades(self, market_id: Optional[str] = None) -> list[Trade]:
        """Get trade history."""
        if market_id:
            return [t for t in self._trades if t.market_id == market_id]
        return self._trades.copy()

    # ==================== Balance Management ====================

    def _update_balance(self, side: OrderSide, price: float, size: float) -> None:
        """Update balance after a trade."""
        cost = price * size
        
        if side == OrderSide.BUY:
            self._balance -= cost
        else:
            self._balance += cost

    @property
    def balance(self) -> float:
        """Get current balance."""
        if self.config.is_paper:
            return self._balance
        return self.client.get_balance()

    @property
    def equity(self) -> float:
        """Get total equity (balance + position value)."""
        position_value = sum(
            pos.size * pos.avg_entry_price
            for pos in self._positions.values()
        )
        return self.balance + position_value

    @property
    def realized_pnl(self) -> float:
        """Get total realized P&L."""
        return sum(pos.realized_pnl for pos in self._positions.values())

    # ==================== Statistics ====================

    def get_stats(self) -> dict:
        """Get execution statistics."""
        trades = self._trades
        
        winning = [t for t in trades if self._is_winning_trade(t)]
        losing = [t for t in trades if not self._is_winning_trade(t)]
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(trades) if trades else 0,
            "total_volume": sum(t.value for t in trades),
            "realized_pnl": self.realized_pnl,
            "current_balance": self.balance,
            "current_equity": self.equity,
        }

    def _is_winning_trade(self, trade: Trade) -> bool:
        """Check if a trade was profitable."""
        # This is a simplified check - real implementation would
        # compare entry and exit prices
        return trade.price > 0.5 if trade.side == OrderSide.BUY else trade.price < 0.5

    def __repr__(self) -> str:
        mode = "paper" if self.config.is_paper else "live"
        return f"OrderExecutor(mode={mode}, balance={self.balance:.2f})"

