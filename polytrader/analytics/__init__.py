"""
Analytics module for Polytrader.

Provides performance metrics, statistical analysis, and visualization tools.
"""

from polytrader.analytics.metrics import (
    calculate_pnl,
    calculate_returns,
    calculate_sharpe,
    calculate_sortino,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_expectancy,
    build_equity_curve,
    calculate_all_metrics,
)

from polytrader.analytics.significance import (
    t_test_returns,
    bootstrap_confidence_interval,
    required_trades_for_significance,
    calculate_statistical_summary,
)

__all__ = [
    # Metrics
    "calculate_pnl",
    "calculate_returns",
    "calculate_sharpe",
    "calculate_sortino",
    "calculate_max_drawdown",
    "calculate_win_rate",
    "calculate_profit_factor",
    "calculate_expectancy",
    "build_equity_curve",
    "calculate_all_metrics",
    # Significance
    "t_test_returns",
    "bootstrap_confidence_interval",
    "required_trades_for_significance",
    "calculate_statistical_summary",
]

