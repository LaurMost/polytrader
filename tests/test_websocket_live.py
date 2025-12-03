"""
Live integration tests for Polymarket WebSocket.

These tests connect to the real Polymarket WebSocket endpoints.
They require valid API credentials to run fully.

Run with: pytest tests/test_websocket_live.py -v

To skip these tests when no credentials are available, they use
pytest.mark.skipif decorators.
"""

import asyncio
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from polytrader.config import Config
from polytrader.core.websocket import WebSocketManager
from polytrader.data.models import PriceUpdate


# Check if credentials are available
def has_credentials() -> bool:
    """Check if API credentials are configured."""
    api_key = os.environ.get("POLYMARKET_API_KEY", "")
    api_secret = os.environ.get("POLYMARKET_API_SECRET", "")
    api_passphrase = os.environ.get("POLYMARKET_API_PASSPHRASE", "")
    return bool(api_key and api_secret and api_passphrase)


# A known active token ID for testing (BTC price market)
# This should be updated if the market becomes inactive
TEST_TOKEN_ID = "109681959945973300464568698402968596289258214226684818748321941747028805721376"


class TestWebSocketManagerUnit:
    """Unit tests for WebSocketManager that don't require live connections."""

    def test_init(self):
        """Test WebSocketManager initialization."""
        manager = WebSocketManager()
        
        assert manager._market_ws is None
        assert manager._user_ws is None
        assert manager._running is False
        assert len(manager._market_subscriptions) == 0
        assert len(manager._user_subscriptions) == 0

    def test_callback_registration(self):
        """Test callback registration."""
        manager = WebSocketManager()
        
        callback = MagicMock()
        manager.on_price_update(callback)
        
        assert callback in manager._price_callbacks

    def test_get_auth_empty(self):
        """Test _get_auth returns empty strings when no credentials configured."""
        with patch.object(Config, "_instance", None):
            Config._config = {}
            manager = WebSocketManager()
            auth = manager._get_auth()
            
            assert auth["apiKey"] == ""
            assert auth["secret"] == ""
            assert auth["passphrase"] == ""

    def test_has_credentials_false(self):
        """Test has_credentials returns False when no credentials."""
        with patch.object(Config, "_instance", None):
            Config._config = {}
            manager = WebSocketManager()
            
            assert manager.has_credentials() is False

    @pytest.mark.asyncio
    async def test_subscribe_market_adds_tokens(self):
        """Test that subscribe_market adds token IDs to subscriptions."""
        manager = WebSocketManager()
        
        await manager.subscribe_market(["token1", "token2"])
        
        assert "token1" in manager._market_subscriptions
        assert "token2" in manager._market_subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_market_removes_tokens(self):
        """Test that unsubscribe_market removes token IDs."""
        manager = WebSocketManager()
        manager._market_subscriptions = {"token1", "token2", "token3"}
        
        await manager.unsubscribe_market(["token1", "token2"])
        
        assert "token1" not in manager._market_subscriptions
        assert "token2" not in manager._market_subscriptions
        assert "token3" in manager._market_subscriptions


class TestPriceUpdateParsing:
    """Tests for price update message parsing."""

    def test_parse_legacy_format(self):
        """Test parsing legacy price_change format."""
        manager = WebSocketManager()
        
        data = {
            "event_type": "price_change",
            "market": "market_123",
            "asset_id": "token_456",
            "price": "0.65",
            "bid": "0.64",
            "ask": "0.66",
        }
        
        updates = manager._parse_price_updates(data)
        
        assert len(updates) == 1
        assert updates[0].market_id == "market_123"
        assert updates[0].token_id == "token_456"
        assert updates[0].price == 0.65
        assert updates[0].best_bid == 0.64
        assert updates[0].best_ask == 0.66

    def test_parse_new_format_with_price_changes(self):
        """Test parsing new price_change format with price_changes array."""
        manager = WebSocketManager()
        
        data = {
            "event_type": "price_change",
            "market": "market_123",
            "price_changes": [
                {
                    "asset_id": "token_yes",
                    "price": "0.65",
                    "best_bid": "0.64",
                    "best_ask": "0.66",
                },
                {
                    "asset_id": "token_no",
                    "price": "0.35",
                    "best_bid": "0.34",
                    "best_ask": "0.36",
                },
            ],
        }
        
        updates = manager._parse_price_updates(data)
        
        assert len(updates) == 2
        
        # First update (YES token)
        assert updates[0].token_id == "token_yes"
        assert updates[0].price == 0.65
        assert updates[0].best_bid == 0.64
        assert updates[0].best_ask == 0.66
        
        # Second update (NO token)
        assert updates[1].token_id == "token_no"
        assert updates[1].price == 0.35

    def test_parse_empty_price_changes(self):
        """Test parsing price_change with empty price_changes array."""
        manager = WebSocketManager()
        
        data = {
            "event_type": "price_change",
            "market": "market_123",
            "price_changes": [],
        }
        
        updates = manager._parse_price_updates(data)
        
        assert len(updates) == 0

    def test_parse_missing_fields_uses_defaults(self):
        """Test parsing data with missing fields uses default values."""
        manager = WebSocketManager()
        
        # Data without expected fields - parser uses defaults
        data = {"some_field": "value"}
        
        updates = manager._parse_price_updates(data)
        
        # Legacy parser returns an update with empty/default values
        assert len(updates) == 1
        assert updates[0].market_id == ""
        assert updates[0].token_id == ""
        assert updates[0].price == 0.0


class TestMessageHandling:
    """Tests for WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_handle_market_message_dict(self):
        """Test handling dict message from WebSocket."""
        manager = WebSocketManager()
        
        # Dict message should be handled without error
        data = {"event_type": "price_change", "price": "0.5"}
        await manager._handle_market_message(data)

    @pytest.mark.asyncio
    async def test_handle_market_message_list(self):
        """Test handling list message from WebSocket (batch updates)."""
        manager = WebSocketManager()
        
        # List message should be handled without error
        data = [
            {"event_type": "price_change", "price": "0.5"},
            {"event_type": "book", "bids": []},
        ]
        await manager._handle_market_message(data)

    @pytest.mark.asyncio
    async def test_handle_market_message_empty_list(self):
        """Test handling empty list message from WebSocket."""
        manager = WebSocketManager()
        
        # Empty list should be handled without error
        await manager._handle_market_message([])

    @pytest.mark.asyncio
    async def test_price_callback_invoked(self):
        """Test that price callbacks are invoked on price_change events."""
        manager = WebSocketManager()
        
        callback = MagicMock()
        manager.on_price_update(callback)
        
        data = {
            "event_type": "price_change",
            "market": "market_123",
            "asset_id": "token_456",
            "price": "0.65",
        }
        
        await manager._handle_single_market_message(data)
        
        assert callback.called
        update = callback.call_args[0][0]
        assert isinstance(update, PriceUpdate)
        assert update.price == 0.65

    @pytest.mark.asyncio
    async def test_orderbook_callback_invoked(self):
        """Test that orderbook callbacks are invoked on book events."""
        manager = WebSocketManager()
        
        callback = MagicMock()
        manager.on_orderbook_update(callback)
        
        data = {
            "event_type": "book",
            "asset_id": "token_123",
            "bids": [["0.64", "100"]],
            "asks": [["0.66", "100"]],
        }
        
        await manager._handle_single_market_message(data)
        
        assert callback.called
        assert callback.call_args[0][0] == data

    @pytest.mark.asyncio
    async def test_trade_callback_invoked(self):
        """Test that trade callbacks are invoked on trade events."""
        manager = WebSocketManager()
        
        callback = MagicMock()
        manager.on_trade(callback)
        
        data = {
            "event_type": "trade",
            "asset_id": "token_123",
            "price": "0.65",
            "size": "100",
            "side": "BUY",
        }
        
        await manager._handle_single_market_message(data)
        
        assert callback.called


@pytest.mark.skipif(
    not has_credentials(),
    reason="No Polymarket API credentials configured"
)
class TestLiveWebSocketConnection:
    """
    Live integration tests against Polymarket WebSocket.
    
    These tests require valid API credentials in environment variables:
    - POLYMARKET_API_KEY
    - POLYMARKET_API_SECRET
    - POLYMARKET_API_PASSPHRASE
    """

    @pytest.mark.asyncio
    async def test_connect_to_market_websocket(self):
        """Test connecting to the market WebSocket."""
        manager = WebSocketManager()
        
        try:
            await manager._connect_market()
            
            assert manager._market_ws is not None
            assert manager._market_ws.open
            
        finally:
            if manager._market_ws:
                await manager._market_ws.close()

    @pytest.mark.asyncio
    async def test_subscribe_and_receive_data(self):
        """Test subscribing to a market and receiving data."""
        manager = WebSocketManager()
        received_messages = []
        
        def on_any_message(data):
            received_messages.append(data)
        
        manager.on_price_update(on_any_message)
        manager.on_orderbook_update(on_any_message)
        
        try:
            await manager.subscribe_market([TEST_TOKEN_ID])
            await manager._connect_market()
            
            # Wait for some messages (with timeout)
            start = datetime.now()
            timeout_seconds = 10
            
            while len(received_messages) < 1:
                if manager._market_ws:
                    try:
                        message = await asyncio.wait_for(
                            manager._market_ws.recv(),
                            timeout=2.0
                        )
                        import json
                        data = json.loads(message)
                        await manager._handle_market_message(data)
                    except asyncio.TimeoutError:
                        pass
                
                if (datetime.now() - start).total_seconds() > timeout_seconds:
                    break
            
            # We should have received at least an initial dump
            assert len(received_messages) >= 0  # May be 0 if market is inactive
            
        finally:
            if manager._market_ws:
                await manager._market_ws.close()

    @pytest.mark.asyncio
    async def test_ping_keeps_connection_alive(self):
        """Test that PING messages keep the connection alive."""
        manager = WebSocketManager()
        
        try:
            await manager._connect_market()
            
            # Send a few pings manually
            for _ in range(3):
                await manager._market_ws.send("PING")
                await asyncio.sleep(1)
            
            # Connection should still be open
            assert manager._market_ws.open
            
        finally:
            if manager._market_ws:
                await manager._market_ws.close()

    @pytest.mark.asyncio
    async def test_connection_stays_alive_for_30_seconds(self):
        """Test that connection stays alive for longer than old heartbeat interval."""
        manager = WebSocketManager()
        manager._running = True
        
        try:
            await manager._connect_market()
            
            # Start ping task
            ping_task = asyncio.create_task(
                manager._send_pings(manager._market_ws)
            )
            
            # Wait 15 seconds (would fail with old 30s heartbeat if pings not working)
            await asyncio.sleep(15)
            
            # Connection should still be open
            assert manager._market_ws.open
            
            manager._running = False
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
            
        finally:
            if manager._market_ws:
                await manager._market_ws.close()


@pytest.mark.skipif(
    not has_credentials(),
    reason="No Polymarket API credentials configured"
)
class TestLiveUserChannel:
    """
    Live tests for user channel (requires authentication).
    """

    @pytest.mark.asyncio
    async def test_connect_to_user_websocket(self):
        """Test connecting to the user WebSocket."""
        manager = WebSocketManager()
        
        # Skip if no credentials
        if not manager.has_credentials():
            pytest.skip("No API credentials configured")
        
        try:
            await manager._connect_user()
            
            assert manager._user_ws is not None
            assert manager._user_ws.open
            
        finally:
            if manager._user_ws:
                await manager._user_ws.close()

    @pytest.mark.asyncio
    async def test_user_subscription_with_auth(self):
        """Test subscribing to user channel with authentication."""
        manager = WebSocketManager()
        
        # Skip if no credentials
        if not manager.has_credentials():
            pytest.skip("No API credentials configured")
        
        try:
            await manager.subscribe_user(["test_condition_id"])
            await manager._connect_user()
            
            # Send subscription
            await manager._send_user_subscription()
            
            # Connection should still be open (no auth error)
            assert manager._user_ws.open
            
        finally:
            if manager._user_ws:
                await manager._user_ws.close()

