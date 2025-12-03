# Polytrader Test Report

**Date:** December 3, 2025  
**Test Framework:** pytest 9.0.1  
**Python Version:** 3.11.13

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 174 |
| Passed | 174 |
| Failed | 0 |
| Errors | 0 |
| Duration | ~1.2s |

## Test Coverage by Module

### CLI Tests (`test_cli.py`)

- 16 tests covering all CLI commands
- Tests: help, version, config, balance, history, orders, positions, stats, market, export, run

### Client Tests (`test_client.py`)

- 7 tests for Polymarket API client
- Tests: initialization, paper mode, market fetching, rate limiting, error handling

### Config Tests (`test_config.py`)

- 11 tests for configuration management
- Tests: singleton pattern, mode detection, get/set methods, env var substitution

### Executor Tests (`test_executor.py`)

- 11 tests for order execution
- Tests: initialization, paper trading, order placement, position tracking

### Helper Tests (`test_helpers.py`)

- 12 tests for utility functions
- Tests: format_amount, format_percentage, format_pnl

### Indicator Tests (`test_indicators.py`)

- 18 tests for technical indicators
- Tests: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ROC, OBV

### Metrics Tests (`test_metrics.py`)

- 17 tests for performance metrics
- Tests: P&L, Sharpe ratio, Sortino ratio, max drawdown, win rate, profit factor, expectancy, equity curve

### Model Tests (`test_models.py`)

- 22 tests for data models
- Tests: Market, Order, Trade, Position, PriceUpdate models and validation

### Significance Tests (`test_significance.py`)

- 15 tests for statistical analysis
- Tests: t-test, bootstrap confidence intervals, required sample size, statistical summary

### Storage Tests (`test_storage.py`)

- 11 tests for data persistence
- Tests: initialization, save/get trades/orders/positions, CSV export, persistence

### Strategy Tests (`test_strategy.py`)

- 12 tests for strategy framework
- Tests: base class, lifecycle hooks, loader, runner, callbacks

### URL Parser Tests (`test_url_parser.py`)

- 11 tests for URL parsing
- Tests: parse_market_url, is_valid_polymarket_url, extract_slug, format_market_summary

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=polytrader --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py -v

# Run specific test class
uv run pytest tests/test_models.py::TestMarketModel -v

# Generate XML report
uv run pytest tests/ --junitxml=test-report.xml
```

## Test Files

| File | Tests | Description |
|------|-------|-------------|
| `tests/__init__.py` | - | Test package init |
| `tests/conftest.py` | - | Shared fixtures |
| `tests/test_cli.py` | 16 | CLI command tests |
| `tests/test_client.py` | 7 | API client tests |
| `tests/test_config.py` | 11 | Configuration tests |
| `tests/test_executor.py` | 11 | Order executor tests |
| `tests/test_helpers.py` | 12 | Utility function tests |
| `tests/test_indicators.py` | 18 | Technical indicator tests |
| `tests/test_metrics.py` | 17 | Performance metrics tests |
| `tests/test_models.py` | 22 | Data model tests |
| `tests/test_significance.py` | 15 | Statistical tests |
| `tests/test_storage.py` | 11 | Storage layer tests |
| `tests/test_strategy.py` | 12 | Strategy framework tests |
| `tests/test_url_parser.py` | 11 | URL parser tests |

## Fixtures

The test suite uses the following shared fixtures defined in `conftest.py`:

- `temp_dir` - Temporary directory for test files
- `temp_db` - Temporary database path
- `temp_config` - Temporary configuration file
- `sample_market` - Sample Market object
- `sample_trade` - Sample Trade object
- `sample_order` - Sample Order object
- `sample_position` - Sample Position object
- `sample_trades` - List of sample trades for analytics testing
- `sample_returns` - Sample return series for statistical testing
- `sample_equity_curve` - Sample equity curve for drawdown testing
- `mock_polymarket_response` - Mock API response
- `price_series` - Sample price series for indicator testing
- `ohlcv_data` - Sample OHLCV data for indicator testing
