"""
Strategy runner for executing strategies with real-time data.
"""

import asyncio
from typing import Optional

from polytrader.config import get_config
from polytrader.core.client import PolymarketClient
from polytrader.core.executor import OrderExecutor
from polytrader.core.websocket import WebSocketManager
from polytrader.data.models import Market, PriceUpdate
from polytrader.strategy.base import Strategy
from polytrader.utils.logging import get_logger
from polytrader.utils.url_parser import get_market_from_url, is_valid_polymarket_url

logger = get_logger(__name__)


class StrategyRunner:
    """
    Runs a strategy with real-time market data.
    
    Usage:
        runner = StrategyRunner(strategy)
        await runner.run()
    """

    def __init__(self, strategy: Strategy):
        """
        Initialize the runner.
        
        Args:
            strategy: Strategy instance to run
        """
        self.strategy = strategy
        self.config = get_config()
        
        self.client = PolymarketClient()
        self.executor = OrderExecutor()
        self.websocket = WebSocketManager()
        
        # Link executor to strategy
        self.strategy._executor = self.executor
        
        self._running = False

    async def run(self) -> None:
        """Run the strategy."""
        logger.info(f"Starting strategy: {self.strategy.name}")
        
        try:
            # Initialize markets
            await self._load_markets()
            
            # Set up WebSocket callbacks
            self._setup_callbacks()
            
            # Subscribe to markets
            token_ids = []
            for market in self.strategy._markets.values():
                token_ids.append(market.token_id_yes)
                token_ids.append(market.token_id_no)
            
            await self.websocket.subscribe_market(token_ids)
            
            # Call strategy start hook
            self.strategy._running = True
            self.strategy.on_start()
            
            # Run main loop
            self._running = True
            
            # Start heartbeat task alongside WebSocket
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            websocket_task = asyncio.create_task(self.websocket.run())
            
            # Wait for either to complete (websocket disconnect or error)
            done, pending = await asyncio.wait(
                [heartbeat_task, websocket_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except KeyboardInterrupt:
            logger.info("Strategy interrupted by user")
        except Exception as e:
            logger.error(f"Strategy error: {e}")
            self.strategy.on_error(e)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the strategy."""
        logger.info(f"Stopping strategy: {self.strategy.name}")
        
        self._running = False
        self.strategy._running = False
        
        # Call strategy stop hook
        self.strategy.on_stop()
        
        # Disconnect WebSocket
        await self.websocket.disconnect()

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to show strategy is alive."""
        heartbeat_interval = self.config.get("strategy.heartbeat_interval", 30)
        
        while self._running:
            await asyncio.sleep(heartbeat_interval)
            
            if not self._running:
                break
            
            # Call strategy heartbeat if it exists
            if hasattr(self.strategy, 'on_heartbeat'):
                try:
                    self.strategy.on_heartbeat()
                except Exception as e:
                    logger.error(f"Error in on_heartbeat: {e}")
            else:
                # Default heartbeat log
                logger.info(
                    f"💓 [{self.strategy.name}] Heartbeat | "
                    f"Markets: {len(self.strategy._markets)} | "
                    f"Positions: {len(self.strategy._positions)} | "
                    f"WS: {'connected' if self.websocket.is_connected else 'disconnected'}"
                )

    async def _load_markets(self) -> None:
        """Load markets specified in the strategy."""
        logger.info(f"Loading {len(self.strategy.markets)} markets...")
        
        for market_ref in self.strategy.markets:
            market = None
            
            # Check if it's a URL
            if is_valid_polymarket_url(market_ref):
                market = get_market_from_url(market_ref)
            else:
                # Try as market ID
                market = self.client.get_market_by_id(market_ref)
            
            if market:
                self.strategy._markets[market.id] = market
                logger.info(f"Loaded market: {market.question[:50]}...")
            else:
                logger.warning(f"Could not load market: {market_ref}")

    def _setup_callbacks(self) -> None:
        """Set up WebSocket callbacks."""
        
        def on_price_update(update: PriceUpdate):
            # Find the market for this update
            for market in self.strategy._markets.values():
                if (
                    market.token_id_yes == update.token_id or
                    market.token_id_no == update.token_id
                ):
                    # Update market prices
                    if market.token_id_yes == update.token_id:
                        market.price_yes = update.price
                    else:
                        market.price_no = update.price
                    
                    # Call strategy hook
                    try:
                        self.strategy.on_price_update(market, update.price)
                    except Exception as e:
                        logger.error(f"Error in on_price_update: {e}")
                        self.strategy.on_error(e)
                    break
        
        def on_orderbook_update(data: dict):
            # Find market and call hook
            asset_id = data.get("asset_id", "")
            for market in self.strategy._markets.values():
                if (
                    market.token_id_yes == asset_id or
                    market.token_id_no == asset_id
                ):
                    try:
                        self.strategy.on_orderbook_update(market, data)
                    except Exception as e:
                        logger.error(f"Error in on_orderbook_update: {e}")
                    break
        
        def on_order_update(data: dict):
            # Handle order updates from user channel
            order_id = data.get("order_id", "")
            if order_id in self.strategy._orders:
                order = self.strategy._orders[order_id]
                event_type = data.get("event_type", "")
                
                if event_type == "order_fill":
                    # Create trade from fill data
                    from polytrader.data.models import Trade, OrderStatus
                    import uuid
                    
                    trade = Trade(
                        id=str(uuid.uuid4()),
                        order_id=order_id,
                        market_id=order.market_id,
                        token_id=order.token_id,
                        side=order.side,
                        price=float(data.get("price", order.price)),
                        size=float(data.get("size", 0)),
                    )
                    
                    order.filled_size += trade.size
                    if order.filled_size >= order.size:
                        order.status = OrderStatus.FILLED
                    
                    self.strategy._trades.append(trade)
                    
                    try:
                        self.strategy.on_fill(order, trade)
                    except Exception as e:
                        logger.error(f"Error in on_fill: {e}")
        
        def on_trade(data: dict):
            # Handle trade events from market channel
            asset_id = data.get("asset_id", "")
            for market in self.strategy._markets.values():
                if (
                    market.token_id_yes == asset_id or
                    market.token_id_no == asset_id
                ):
                    try:
                        if hasattr(self.strategy, 'on_market_trade'):
                            self.strategy.on_market_trade(market, data)
                    except Exception as e:
                        logger.error(f"Error in on_market_trade: {e}")
                    break
        
        # Register callbacks
        self.websocket.on_price_update(on_price_update)
        self.websocket.on_orderbook_update(on_orderbook_update)
        self.websocket.on_trade(on_trade)
        self.websocket.on_order_update(on_order_update)

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"StrategyRunner(strategy={self.strategy.name}, status={status})"

