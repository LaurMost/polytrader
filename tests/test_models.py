"""
Tests for polytrader.data.models module.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError


class TestMarketModel:
    """Tests for Market data model."""
    
    def test_market_creation(self):
        """Test creating a Market instance."""
        from polytrader.data.models import Market
        
        market = Market(
            id="test_123",
            condition_id="cond_123",
            question="Will it rain?",
            slug="will-it-rain",
            token_id_yes="token_yes",
            token_id_no="token_no",
            price_yes=0.65,
            price_no=0.35,
        )
        
        assert market.id == "test_123"
        assert market.question == "Will it rain?"
        assert market.price_yes == 0.65
        assert market.price_no == 0.35
    
    def test_market_with_optional_fields(self):
        """Test Market with optional fields."""
        from polytrader.data.models import Market
        
        market = Market(
            id="test_market_123",
            condition_id="cond_123",
            question="Will Bitcoin reach $100k by end of 2024?",
            slug="bitcoin-100k-2024",
            token_id_yes="token_yes_123",
            token_id_no="token_no_123",
            price_yes=0.65,
            price_no=0.35,
            volume=1000000.0,
            liquidity=500000.0,
            closed=False,
        )
        
        assert market.volume == 1000000.0
        assert market.liquidity == 500000.0
        assert market.closed == False
    
    def test_market_default_values(self):
        """Test Market default values."""
        from polytrader.data.models import Market
        
        market = Market(
            id="test",
            condition_id="cond",
            question="Test?",
            slug="test",
            token_id_yes="yes",
            token_id_no="no",
            price_yes=0.5,
            price_no=0.5,
        )
        
        assert market.volume == 0.0
        assert market.liquidity == 0.0
        assert market.closed == False
    
    def test_market_url_property(self):
        """Test Market URL property."""
        from polytrader.data.models import Market
        
        market = Market(
            id="test",
            condition_id="cond",
            question="Test?",
            slug="test-market",
            token_id_yes="yes",
            token_id_no="no",
        )
        
        assert "test-market" in market.url


class TestOrderModel:
    """Tests for Order data model."""
    
    def test_order_creation(self):
        """Test creating an Order instance."""
        from polytrader.data.models import Order, OrderSide, OrderStatus, OrderType
        
        order = Order(
            id="order_123",
            market_id="market_123",
            token_id="token_123",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING,
            price=0.50,
            size=100.0,
        )
        
        assert order.id == "order_123"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.PENDING
        assert order.price == 0.50
        assert order.size == 100.0
    
    def test_order_sides(self):
        """Test OrderSide enum values."""
        from polytrader.data.models import OrderSide
        
        assert OrderSide.BUY.value == "BUY"
        assert OrderSide.SELL.value == "SELL"
    
    def test_order_statuses(self):
        """Test OrderStatus enum values."""
        from polytrader.data.models import OrderStatus
        
        assert OrderStatus.PENDING.value == "PENDING"
        assert OrderStatus.OPEN.value == "OPEN"
        assert OrderStatus.FILLED.value == "FILLED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"
    
    def test_order_filled_size_default(self):
        """Test Order filled_size default."""
        from polytrader.data.models import Order, OrderSide, OrderStatus, OrderType
        
        order = Order(
            id="test",
            market_id="market",
            token_id="token",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=0.5,
            size=100,
            status=OrderStatus.PENDING,
        )
        
        assert order.filled_size == 0.0
    
    def test_order_remaining_size(self):
        """Test Order remaining_size property."""
        from polytrader.data.models import Order, OrderSide, OrderStatus, OrderType
        
        order = Order(
            id="test",
            market_id="market",
            token_id="token",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=0.5,
            size=100,
            filled_size=40,
            status=OrderStatus.PARTIALLY_FILLED,
        )
        
        assert order.remaining_size == 60.0


class TestTradeModel:
    """Tests for Trade data model."""
    
    def test_trade_creation(self, sample_trade):
        """Test creating a Trade instance."""
        from polytrader.data.models import OrderSide
        
        assert sample_trade.id == "trade_123"
        assert sample_trade.side == OrderSide.BUY
        assert sample_trade.price == 0.50
        assert sample_trade.size == 100.0
        assert sample_trade.is_paper == True
    
    def test_trade_value_calculation(self, sample_trade):
        """Test Trade value property."""
        expected_value = 0.50 * 100.0  # price * size
        assert sample_trade.value == expected_value
    
    def test_trade_with_execution_time(self, sample_trade):
        """Test Trade with execution time."""
        assert sample_trade.executed_at is not None
        assert isinstance(sample_trade.executed_at, datetime)


class TestPositionModel:
    """Tests for Position data model."""
    
    def test_position_creation(self):
        """Test creating a Position instance."""
        from polytrader.data.models import Position
        
        position = Position(
            token_id="token_123",
            market_id="market_123",
            size=100.0,
            avg_entry_price=0.50,
        )
        
        assert position.token_id == "token_123"
        assert position.size == 100.0
        assert position.avg_entry_price == 0.50
        assert position.cost_basis == 50.0
    
    def test_position_unrealized_pnl(self):
        """Test Position unrealized P&L calculation."""
        from polytrader.data.models import Position
        
        position = Position(
            token_id="token",
            market_id="market",
            size=100.0,
            avg_entry_price=0.40,
        )
        
        # Unrealized P&L = (current_price - avg_entry) * size
        expected_pnl = (0.50 - 0.40) * 100.0
        assert position.unrealized_pnl(0.50) == expected_pnl
    
    def test_position_default_values(self):
        """Test Position default values."""
        from polytrader.data.models import Position
        
        position = Position(
            token_id="token",
            market_id="market",
            size=100.0,
            avg_entry_price=0.50,
        )
        
        assert position.realized_pnl == 0.0
    
    def test_position_is_long(self):
        """Test Position is_long property."""
        from polytrader.data.models import Position
        
        position = Position(
            token_id="token",
            market_id="market",
            size=100.0,
            avg_entry_price=0.50,
        )
        
        assert position.is_long == True
        assert position.is_short == False
    
    def test_position_is_flat(self):
        """Test Position is_flat property."""
        from polytrader.data.models import Position
        
        position = Position(
            token_id="token",
            market_id="market",
            size=0.0,
            avg_entry_price=0.50,
        )
        
        assert position.is_flat == True


class TestPriceUpdateModel:
    """Tests for PriceUpdate data model."""
    
    def test_price_update_creation(self):
        """Test creating a PriceUpdate instance."""
        from polytrader.data.models import PriceUpdate
        
        update = PriceUpdate(
            market_id="market_123",
            token_id="token_123",
            price=0.65,
        )
        
        assert update.token_id == "token_123"
        assert update.price == 0.65
    
    def test_price_update_with_bid_ask(self):
        """Test PriceUpdate with bid/ask."""
        from polytrader.data.models import PriceUpdate
        
        update = PriceUpdate(
            market_id="market",
            token_id="token",
            price=0.50,
            best_bid=0.49,
            best_ask=0.51,
        )
        
        assert update.best_bid == 0.49
        assert update.best_ask == 0.51
        assert abs(update.spread - 0.02) < 0.001  # Float comparison


class TestModelSerialization:
    """Tests for model serialization."""
    
    def test_market_repr(self):
        """Test Market repr."""
        from polytrader.data.models import Market
        
        market = Market(
            id="test_market_123",
            condition_id="cond_123",
            question="Will Bitcoin reach $100k by end of 2024?",
            slug="bitcoin-100k-2024",
            token_id_yes="token_yes_123",
            token_id_no="token_no_123",
            price_yes=0.65,
            price_no=0.35,
        )
        
        repr_str = repr(market)
        assert "test_market_123" in repr_str
    
    def test_trade_repr(self, sample_trade):
        """Test Trade repr."""
        repr_str = repr(sample_trade)
        
        assert "trade_123" in repr_str
    
    def test_order_repr(self, sample_order):
        """Test Order repr."""
        repr_str = repr(sample_order)
        
        assert "order_123" in repr_str


class TestModelValidation:
    """Tests for model validation."""
    
    def test_invalid_price_range(self):
        """Test that prices outside valid range are handled."""
        from polytrader.data.models import Market
        
        # Prices can be any float, validation depends on business logic
        market = Market(
            id="test",
            condition_id="cond",
            question="Test?",
            slug="test",
            token_id_yes="yes",
            token_id_no="no",
            price_yes=1.5,  # > 1.0
            price_no=-0.5,  # < 0.0
        )
        
        # Model should still be created (validation is business logic)
        assert market.price_yes == 1.5
    
    def test_required_fields(self):
        """Test that required fields raise errors when missing."""
        from polytrader.data.models import Market
        
        with pytest.raises(TypeError):
            Market(
                id="test",
                # Missing required fields
            )

