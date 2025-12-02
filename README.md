# Polytrader

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A professional quantitative trading framework for [Polymarket](https://polymarket.com) prediction markets. Build, backtest, and deploy algorithmic trading strategies with real-time data, paper trading, and comprehensive analytics.

## Features

- **Strategy Framework** - Abstract base class with lifecycle hooks for clean strategy development
- **Real-time Data** - WebSocket integration for live market prices and order book updates
- **Paper Trading** - Test strategies with simulated execution before going live
- **Performance Analytics** - Sharpe ratio, drawdown, win rate, and statistical significance testing
- **Web Dashboard** - Streamlit-based UI for monitoring performance and visualizing results
- **CLI Interface** - Full-featured command-line tool for all operations
- **Technical Indicators** - Built-in SMA, EMA, RSI, MACD, Bollinger Bands, and more

## Quick Start

### Installation with uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager that ensures reproducible installs with no dependency conflicts.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/YOUR_USERNAME/polytrader.git
cd polytrader

# Create virtual environment and install dependencies
uv sync

# Verify installation
uv run polytrader --help
```

### Alternative: pip installation

```bash
git clone https://github.com/YOUR_USERNAME/polytrader.git
cd polytrader
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Configuration

Copy the example config and add your credentials:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
# API Configuration
polymarket:
  host: "https://clob.polymarket.com"
  chain_id: 137

# Trading Mode
mode: "paper"  # "paper" or "live"

# Paper Trading Settings
paper_trading:
  initial_balance: 10000.0
```

For live trading, set your private key as an environment variable:

```bash
export POLYMARKET_PRIVATE_KEY="your_private_key_here"
```

## Usage

### Run a Strategy

```bash
# Paper trading (default)
polytrader run strategies/example_strategy.py

# Live trading (use with caution!)
polytrader run strategies/my_strategy.py --live
```

### View Market Information

```bash
# Get details for a specific market
polytrader market https://polymarket.com/event/bitcoin-100k

# List available markets
polytrader markets --limit 20

# Watch live prices
polytrader watch https://polymarket.com/event/bitcoin-100k --live
```

### Performance Analytics

```bash
# View stats in terminal
polytrader stats

# Export stats as JSON
polytrader stats --json

# Launch web dashboard
polytrader dashboard
```

### Account Management

```bash
# Check balance
polytrader balance

# View open orders
polytrader orders

# View positions
polytrader positions

# View trade history
polytrader history --limit 50

# Export data
polytrader export --all --output ./exports
```

## Writing Strategies

Create a new strategy by extending the `Strategy` base class:

```python
from polytrader.strategy.base import Strategy
from polytrader.data.models import PriceUpdate

class MyStrategy(Strategy):
    name = "my_strategy"
    markets = ["https://polymarket.com/event/your-market"]
    
    def on_start(self):
        """Called when strategy starts."""
        self.log.info("Strategy started!")
    
    def on_price_update(self, update: PriceUpdate):
        """Called on every price update."""
        if update.price < 0.30:
            self.buy(update.token_id, size=10, price=update.price)
        elif update.price > 0.70:
            self.sell(update.token_id, size=10, price=update.price)
    
    def on_fill(self, trade):
        """Called when an order is filled."""
        self.log.info(f"Trade executed: {trade}")
```

See `strategies/example_strategy.py` for more examples including momentum and ML-based strategies.

## Dashboard

Launch the performance dashboard to visualize your trading results:

```bash
polytrader dashboard
```

The dashboard includes:
- Key metrics (P&L, Sharpe, Win Rate, Max Drawdown)
- Interactive equity curve
- P&L distribution analysis
- Statistical significance testing (t-test, confidence intervals)
- Trade history and export functionality

## Project Structure

```
polytrader/
├── polytrader/
│   ├── analytics/        # Performance metrics & statistics
│   ├── core/             # Client, executor, WebSocket
│   ├── data/             # Models, storage, market data
│   ├── indicators/       # Technical indicators
│   ├── strategy/         # Base class, loader, runner
│   ├── utils/            # Helpers, logging, URL parser
│   ├── cli.py            # Command-line interface
│   └── config.py         # Configuration management
├── strategies/           # Your trading strategies
├── dashboard.py          # Streamlit web dashboard
├── pyproject.toml        # Project configuration
└── uv.lock               # Locked dependencies
```

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync --all-extras

# Run linter
uv run ruff check .

# Run type checker
uv run mypy polytrader

# Run tests
uv run pytest
```

### Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Disclaimer

**This software is for educational and research purposes only.** 

- Trading prediction markets involves significant financial risk
- Past performance does not guarantee future results
- Always start with paper trading before using real funds
- The authors are not responsible for any financial losses

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Polymarket](https://polymarket.com) for the prediction market platform
- [py-clob-client](https://github.com/Polymarket/py-clob-client) for the official Python client
