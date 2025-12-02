# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [0.1.0] - 2024-12-02

### Added

#### Core Framework
- Initial project structure with modular architecture
- Configuration management with YAML and environment variable support
- Polymarket client wrapper with rate limiting and retry logic
- WebSocket manager for real-time market and user data
- Order execution engine with paper trading simulation
- SQLite-based storage for trades, orders, and positions
- CSV export functionality for all data types

#### Strategy Framework
- Abstract `Strategy` base class with lifecycle hooks
- Dynamic strategy loading from Python files
- Strategy runner with WebSocket integration
- Event-driven architecture (`on_start`, `on_price_update`, `on_fill`, etc.)

#### Technical Indicators
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Relative Strength Index (RSI)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Average True Range (ATR)
- Rate of Change (ROC)
- On-Balance Volume (OBV)

#### Analytics & Dashboard
- Performance metrics: P&L, Sharpe ratio, Sortino ratio, max drawdown
- Win rate, profit factor, and expectancy calculations
- Statistical significance testing (t-test, bootstrap confidence intervals)
- Streamlit-based web dashboard with interactive charts
- Equity curve visualization
- P&L distribution analysis

#### CLI Interface
- `polytrader run` - Execute trading strategies
- `polytrader market` - Get market details from URL
- `polytrader markets` - List available markets
- `polytrader watch` - Watch live market prices
- `polytrader balance` - Show account balance
- `polytrader orders` - List open orders
- `polytrader positions` - List open positions
- `polytrader history` - View trade history
- `polytrader export` - Export data to CSV
- `polytrader stats` - Show performance statistics
- `polytrader dashboard` - Launch web dashboard
- `polytrader config` - Show current configuration

#### Utilities
- URL parser for extracting market details from Polymarket URLs
- Structured logging with loguru and rich
- Helper functions for formatting amounts and percentages

#### Example Strategies
- Momentum strategy example
- Simple value strategy example
- ML strategy template
- BTC term structure arbitrage strategy

### Security
- Environment variable support for private keys
- Paper trading mode for safe testing
- No hardcoded credentials

---

## Version History

- **0.1.0** - Initial release with core functionality

[Unreleased]: https://github.com/YOUR_USERNAME/polytrader/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YOUR_USERNAME/polytrader/releases/tag/v0.1.0

