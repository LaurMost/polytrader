"""
WebSocket manager for Polymarket real-time data.

Handles connections to market and user channels for live updates.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from polytrader.config import get_config
from polytrader.data.models import PriceUpdate
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections to Polymarket.
    
    Supports two channels:
    - market: Real-time price and orderbook updates
    - user: Order fills and position updates
    
    Usage:
        manager = WebSocketManager()
        
        @manager.on_price_update
        def handle_price(update: PriceUpdate):
            print(f"Price update: {update}")
        
        await manager.subscribe_market(["token_id_1", "token_id_2"])
        await manager.run()
    """

    WSS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    USER_WSS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"

    def __init__(self):
        self.config = get_config()
        
        # Connection state
        self._market_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._user_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        
        # Subscriptions
        self._market_subscriptions: set[str] = set()  # Token IDs
        self._user_subscriptions: set[str] = set()    # Condition IDs
        
        # Callbacks
        self._price_callbacks: list[Callable[[PriceUpdate], None]] = []
        self._orderbook_callbacks: list[Callable[[dict], None]] = []
        self._trade_callbacks: list[Callable[[dict], None]] = []
        self._order_callbacks: list[Callable[[dict], None]] = []
        
        # Reconnection settings
        self._auto_reconnect = self.config.get("websocket.auto_reconnect", True)
        self._reconnect_delay = self.config.get("websocket.reconnect_delay", 5)
        self._ping_interval = self.config.get("websocket.ping_interval", 5)  # Polymarket requires 5s
        
        # Ping tasks
        self._ping_tasks: list[asyncio.Task] = []


        # Cache config key lookups for auth
        _api_key = getattr(self.config, "api_key", None)
        _api_secret = getattr(self.config, "api_secret", None)
        _api_passphrase = getattr(self.config, "api_passphrase", None)
        self._auth: dict[str, str] = {
            "apiKey": _api_key,
            "secret": _api_secret,
            "passphrase": _api_passphrase,
        }

    # ==================== Callback Registration ====================

    def on_price_update(self, callback: Callable[[PriceUpdate], None]) -> None:
        """Register a callback for price updates."""
        self._price_callbacks.append(callback)

    def on_orderbook_update(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for orderbook updates."""
        self._orderbook_callbacks.append(callback)

    def on_trade(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for trade events."""
        self._trade_callbacks.append(callback)

    def on_order_update(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for order updates (user channel)."""
        self._order_callbacks.append(callback)

    # ==================== Subscription Management ====================

    async def subscribe_market(self, token_ids: list[str]) -> None:
        """
        Subscribe to market data for specific tokens.
        
        Args:
            token_ids: List of token IDs to subscribe to
        """
        self._market_subscriptions.update(token_ids)
        
        if self._market_ws and self._market_ws.open:
            await self._send_market_subscription()

    async def unsubscribe_market(self, token_ids: list[str]) -> None:
        """Unsubscribe from market data for specific tokens."""
        self._market_subscriptions.difference_update(token_ids)

    async def subscribe_user(self, condition_ids: list[str]) -> None:
        """
        Subscribe to user channel for specific markets.
        
        Args:
            condition_ids: List of condition IDs to subscribe to
        """
        self._user_subscriptions.update(condition_ids)
        
        if self._user_ws and self._user_ws.open:
            await self._send_user_subscription()

    # ==================== Connection Management ====================

    async def connect(self) -> None:
        """Establish WebSocket connections."""
        await self._connect_market()
        
        # Only connect user channel if we have a private key
        if self.config.private_key:
            await self._connect_user()

    async def _connect_market(self) -> None:
        """Connect to market WebSocket."""
        try:
            # Disable library-level ping; we send explicit PING messages per Polymarket docs
            self._market_ws = await websockets.connect(
                self.WSS_URL,
                ping_interval=None,
                ping_timeout=None,
            )
            logger.info("Connected to market WebSocket")
            
            if self._market_subscriptions:
                await self._send_market_subscription()
                
        except Exception as e:
            logger.error(f"Failed to connect to market WebSocket: {e}")
            raise

    async def _connect_user(self) -> None:
        """Connect to user WebSocket."""
        try:
            # Disable library-level ping; we send explicit PING messages per Polymarket docs
            self._user_ws = await websockets.connect(
                self.USER_WSS_URL,
                ping_interval=None,
                ping_timeout=None,
            )
            logger.info("Connected to user WebSocket")
            
            if self._user_subscriptions:
                await self._send_user_subscription()
                
        except Exception as e:
            logger.error(f"Failed to connect to user WebSocket: {e}")

    async def _send_market_subscription(self) -> None:
        """Send market subscription message."""
        if not self._market_ws or not self._market_subscriptions:
            return
        
        # Build subscription message per Polymarket docs
        message: dict[str, Any] = {
            "assets_ids": list(self._market_subscriptions),
            "type": "MARKET",
            "initial_dump": True,  # Receive initial orderbook state
        }
        
        # Include auth if credentials are available
        auth = self._get_auth()
        if auth.get("apiKey"):
            message["auth"] = auth
        
        await self._market_ws.send(json.dumps(message))
        logger.debug(f"Subscribed to {len(self._market_subscriptions)} markets")

    async def _send_user_subscription(self) -> None:
        """Send user subscription message with authentication."""
        if not self._user_ws:
            return
        
        # Get auth credentials
        auth = self._get_auth()
        if not auth.get("apiKey"):
            logger.warning("No API credentials configured for user channel")
            return
        
        message = {
            "auth": auth,
            "markets": list(self._user_subscriptions),
            "type": "USER",
        }
        
        await self._user_ws.send(json.dumps(message))
        logger.debug(f"Subscribed to user channel for {len(self._user_subscriptions)} markets")

    def _get_auth(self) -> dict[str, str]:
        """
        Get authentication credentials for WebSocket channels.
        
        Returns dict with apiKey, secret, and passphrase as required by Polymarket.
        These credentials can be obtained from py-clob-client or set manually in config.
        """
        return self._auth
    
    def has_credentials(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.config.api_key and self.config.api_secret and self.config.api_passphrase)

    async def disconnect(self) -> None:
        """Close WebSocket connections."""
        self._running = False
        
        # Cancel ping tasks
        for task in self._ping_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._ping_tasks.clear()
        
        if self._market_ws:
            await self._market_ws.close()
            self._market_ws = None
        
        if self._user_ws:
            await self._user_ws.close()
            self._user_ws = None
        
        logger.info("Disconnected from WebSockets")

    # ==================== Message Processing ====================

    async def run(self) -> None:
        """Main loop for processing WebSocket messages."""
        self._running = True
        
        while self._running:
            try:
                await self.connect()
                
                # Create tasks for message processing and ping sending
                tasks = []
                
                if self._market_ws:
                    tasks.append(asyncio.create_task(self._process_market_messages()))
                    ping_task = asyncio.create_task(self._send_pings(self._market_ws))
                    self._ping_tasks.append(ping_task)
                    tasks.append(ping_task)
                
                if self._user_ws:
                    tasks.append(asyncio.create_task(self._process_user_messages()))
                    ping_task = asyncio.create_task(self._send_pings(self._user_ws))
                    self._ping_tasks.append(ping_task)
                    tasks.append(ping_task)
                
                if tasks:
                    await asyncio.gather(*tasks)
                    
            except ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self._cancel_ping_tasks()
                
                if self._auto_reconnect and self._running:
                    logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                    await asyncio.sleep(self._reconnect_delay)
                else:
                    break
                    
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self._cancel_ping_tasks()
                
                if self._auto_reconnect and self._running:
                    await asyncio.sleep(self._reconnect_delay)
                else:
                    break
    
    async def _send_pings(self, ws: Any) -> None:
        """
        Send explicit PING messages to keep connection alive.
        
        Polymarket requires PING messages every 5 seconds (not protocol-level pings).
        """
        while self._running and ws and ws.open:
            try:
                await ws.send("PING")
                logger.debug("Sent PING")
                await asyncio.sleep(self._ping_interval)
            except ConnectionClosed:
                break
            except Exception as e:
                logger.warning(f"Ping error: {e}")
                break
    
    def _cancel_ping_tasks(self) -> None:
        """Cancel all running ping tasks."""
        for task in self._ping_tasks:
            if not task.done():
                task.cancel()
        self._ping_tasks.clear()

    async def _process_market_messages(self) -> None:
        """Process messages from market channel."""
        if not self._market_ws:
            return
        
        async for message in self._market_ws:
            try:
                data = json.loads(message)
                await self._handle_market_message(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from market channel: {message}")
            except Exception as e:
                logger.error(f"Error processing market message: {e}")

    async def _process_user_messages(self) -> None:
        """Process messages from user channel."""
        if not self._user_ws:
            return
        
        async for message in self._user_ws:
            try:
                data = json.loads(message)
                await self._handle_user_message(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from user channel: {message}")
            except Exception as e:
                logger.error(f"Error processing user message: {e}")

    async def _handle_market_message(self, data: Any) -> None:
        """Handle a message from the market channel."""
        # Handle list of messages (batch updates from Polymarket)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    await self._handle_single_market_message(item)
            return
        
        # Handle single message
        if isinstance(data, dict):
            await self._handle_single_market_message(data)

    async def _handle_single_market_message(self, data: dict) -> None:
        """Handle a single market message."""
        event_type = data.get("event_type", "")
        
        if event_type == "price_change":
            # Parse price updates (handles both old and new format)
            updates = self._parse_price_updates(data)
            for update in updates:
                for callback in self._price_callbacks:
                    try:
                        callback(update)
                    except Exception as e:
                        logger.error(f"Price callback error: {e}")
        
        elif event_type == "book":
            for callback in self._orderbook_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Orderbook callback error: {e}")
        
        elif event_type == "trade":
            for callback in self._trade_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Trade callback error: {e}")

    async def _handle_user_message(self, data: dict) -> None:
        """Handle a message from the user channel."""
        event_type = data.get("event_type", "")
        
        if event_type in ("order", "order_fill", "order_cancel"):
            for callback in self._order_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Order callback error: {e}")

    def _parse_price_updates(self, data: dict) -> list[PriceUpdate]:
        """
        Parse price update message(s).
        
        Handles both old format (single update) and new format (price_changes array).
        The new format (Sept 2025) has asset_id inside each price_change object.
        """
        updates = []
        
        try:
            # New format: price_changes array with asset_id inside each change
            if "price_changes" in data:
                market_id = data.get("market", "")
                for pc in data["price_changes"]:
                    update = self._parse_single_price_change(pc, market_id)
                    if update:
                        updates.append(update)
            else:
                # Legacy format: single update with asset_id at top level
                update = self._parse_legacy_price_update(data)
                if update:
                    updates.append(update)
                    
        except Exception as e:
            logger.error(f"Failed to parse price update: {e}")
            
        return updates
    
    def _parse_single_price_change(self, pc: dict, market_id: str) -> Optional[PriceUpdate]:
        """Parse a single price change from the new format."""
        try:
            return PriceUpdate(
                market_id=market_id,
                token_id=pc.get("asset_id", ""),
                price=float(pc.get("price", 0)),
                timestamp=datetime.now(),
                best_bid=float(pc["best_bid"]) if "best_bid" in pc else None,
                best_ask=float(pc["best_ask"]) if "best_ask" in pc else None,
            )
        except Exception as e:
            logger.error(f"Failed to parse price change: {e}")
            return None
    
    def _parse_legacy_price_update(self, data: dict) -> Optional[PriceUpdate]:
        """Parse a price update in the legacy format."""
        try:
            return PriceUpdate(
                market_id=data.get("market", ""),
                token_id=data.get("asset_id", ""),
                price=float(data.get("price", 0)),
                timestamp=datetime.now(),
                best_bid=float(data["bid"]) if "bid" in data else None,
                best_ask=float(data["ask"]) if "ask" in data else None,
            )
        except Exception as e:
            logger.error(f"Failed to parse legacy price update: {e}")
            return None

    # ==================== Utility Methods ====================

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return (
            (self._market_ws is not None and self._market_ws.open) or
            (self._user_ws is not None and self._user_ws.open)
        )

    def __repr__(self) -> str:
        status = "connected" if self.is_connected else "disconnected"
        return f"WebSocketManager(status={status}, markets={len(self._market_subscriptions)})"

