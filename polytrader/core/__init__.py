"""Core trading components."""

# Lazy imports to avoid circular dependencies
__all__ = ["PolymarketClient", "WebSocketManager", "OrderExecutor"]


def __getattr__(name):
    if name == "PolymarketClient":
        from polytrader.core.client import PolymarketClient
        return PolymarketClient
    elif name == "WebSocketManager":
        from polytrader.core.websocket import WebSocketManager
        return WebSocketManager
    elif name == "OrderExecutor":
        from polytrader.core.executor import OrderExecutor
        return OrderExecutor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

