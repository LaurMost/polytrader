"""Data models and storage."""

from polytrader.data.models import Market, Order, Trade, Position, OrderSide, OrderStatus
from polytrader.data.storage import Storage

__all__ = [
    "Market",
    "Order",
    "Trade",
    "Position",
    "OrderSide",
    "OrderStatus",
    "Storage",
]


def get_market_fetcher():
    """Lazy import to avoid circular dependency."""
    from polytrader.data.market import MarketDataFetcher
    return MarketDataFetcher()

