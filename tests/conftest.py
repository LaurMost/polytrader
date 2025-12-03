"""
Shared pytest fixtures for Polytrader tests.
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

# Add polytrader to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database path."""
    return temp_dir / "test.db"


@pytest.fixture
def temp_config(temp_dir):
    """Create a temporary config file."""
    config_path = temp_dir / "config.yaml"
    config_content = f"""
mode: paper

api:
  private_key: test_key
  chain_id: 137
  host: https://clob.polymarket.com

paper:
  starting_balance: 10000.0
  slippage: 0.001

storage:
  data_dir: {temp_dir}
  database: test.db
  csv_dir: exports

logging:
  level: DEBUG
  console_format: simple
"""
    
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_market():
    """Create a sample market object."""
    from polytrader.data.models import Market
    
    return Market(
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


@pytest.fixture
def sample_trade():
    """Create a sample trade object."""
    from polytrader.data.models import Trade, OrderSide
    
    return Trade(
        id="trade_123",
        order_id="order_123",
        market_id="market_123",
        token_id="token_123",
        side=OrderSide.BUY,
        price=0.50,
        size=100.0,
        is_paper=True,
        executed_at=datetime.now(),
    )


@pytest.fixture
def sample_order():
    """Create a sample order object."""
    from polytrader.data.models import Order, OrderSide, OrderStatus, OrderType
    
    return Order(
        id="order_123",
        market_id="market_123",
        token_id="token_123",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=0.50,
        size=100.0,
        status=OrderStatus.PENDING,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_position():
    """Create a sample position object."""
    from polytrader.data.models import Position
    
    return Position(
        token_id="token_123",
        market_id="market_123",
        size=100.0,
        avg_entry_price=0.50,
        realized_pnl=0.0,
    )


@pytest.fixture
def sample_trades():
    """Create a list of sample trades for analytics testing."""
    from polytrader.data.models import Trade, OrderSide
    
    trades = []
    base_time = datetime.now() - timedelta(days=7)
    
    # Create paired buy/sell trades
    for i in range(20):
        buy_price = 0.40 + (i % 5) * 0.05
        sell_price = buy_price + (0.05 if i % 3 != 0 else -0.03)  # Mix of wins/losses
        size = 50.0 + i * 5
        
        trades.append(Trade(
            id=f"buy_{i}",
            order_id=f"order_buy_{i}",
            market_id=f"market_{i % 3}",
            token_id=f"token_{i % 3}",
            side=OrderSide.BUY,
            price=buy_price,
            size=size,
            is_paper=True,
            executed_at=base_time + timedelta(hours=i * 2),
        ))
        
        trades.append(Trade(
            id=f"sell_{i}",
            order_id=f"order_sell_{i}",
            market_id=f"market_{i % 3}",
            token_id=f"token_{i % 3}",
            side=OrderSide.SELL,
            price=sell_price,
            size=size,
            is_paper=True,
            executed_at=base_time + timedelta(hours=i * 2 + 1),
        ))
    
    return trades


@pytest.fixture
def sample_returns():
    """Create sample return series for statistical testing."""
    import numpy as np
    np.random.seed(42)
    
    # Generate returns with slight positive bias
    returns = np.random.normal(0.001, 0.02, 100)
    return pd.Series(returns)


@pytest.fixture
def sample_equity_curve():
    """Create sample equity curve for drawdown testing."""
    import numpy as np
    
    # Simulate equity curve with drawdown
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    equity = [10000.0]
    
    np.random.seed(42)
    for i in range(99):
        change = np.random.normal(0.001, 0.02)
        equity.append(equity[-1] * (1 + change))
    
    return pd.DataFrame({"date": dates, "equity": equity})


@pytest.fixture
def mock_polymarket_response():
    """Mock response from Polymarket API."""
    return {
        "id": "market_123",
        "question": "Test Market?",
        "slug": "test-market",
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.65", "0.35"],
        "volume": "1000000",
        "liquidity": "500000",
        "closed": False,
        "clobTokenIds": '["token_yes", "token_no"]',
    }


@pytest.fixture
def price_series():
    """Create sample price series for indicator testing."""
    import numpy as np
    np.random.seed(42)
    
    # Generate random walk price series
    prices = [100.0]
    for _ in range(99):
        change = np.random.normal(0, 0.02)
        prices.append(prices[-1] * (1 + change))
    
    return pd.Series(prices)


@pytest.fixture
def ohlcv_data():
    """Create sample OHLCV data for indicator testing."""
    import numpy as np
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    
    close = [100.0]
    for _ in range(99):
        change = np.random.normal(0, 0.02)
        close.append(close[-1] * (1 + change))
    
    close = np.array(close)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, 100)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, 100)))
    open_ = (close + np.random.normal(0, 0.005, 100) * close)
    volume = np.random.randint(1000, 10000, 100)
    
    return pd.DataFrame({
        "date": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })

