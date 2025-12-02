"""
Polytrader - A quantitative trading tool for Polymarket prediction markets.

This package provides:
- Real-time WebSocket data streaming
- Paper and live trading modes
- Strategy development framework
- Market data utilities
- Comprehensive logging and storage
"""

__version__ = "0.1.0"
__author__ = "Laurence"

from polytrader.strategy.base import Strategy
from polytrader.data.models import Market, Order, Trade, Position

__all__ = [
    "Strategy",
    "Market",
    "Order",
    "Trade",
    "Position",
    "__version__",
]

