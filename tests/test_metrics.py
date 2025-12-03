"""
Tests for polytrader.analytics.metrics module.
"""

import pytest
import numpy as np
import pandas as pd


class TestCalculatePnL:
    """Tests for P&L calculation."""
    
    def test_pnl_empty_trades(self):
        """Test P&L with no trades."""
        from polytrader.analytics.metrics import calculate_pnl
        
        result = calculate_pnl([])
        
        assert result["total_pnl"] == 0.0
        assert result["num_trades"] == 0
    
    def test_pnl_with_trades(self, sample_trades):
        """Test P&L calculation with trades."""
        from polytrader.analytics.metrics import calculate_pnl
        
        result = calculate_pnl(sample_trades)
        
        assert "total_pnl" in result
        assert "gross_profit" in result
        assert "gross_loss" in result
        assert result["num_trades"] == len(sample_trades)


class TestCalculateSharpe:
    """Tests for Sharpe ratio calculation."""
    
    def test_sharpe_empty_returns(self):
        """Test Sharpe with empty returns."""
        from polytrader.analytics.metrics import calculate_sharpe
        
        result = calculate_sharpe(pd.Series(dtype=float))
        
        assert result == 0.0
    
    def test_sharpe_positive_returns(self, sample_returns):
        """Test Sharpe with positive returns."""
        from polytrader.analytics.metrics import calculate_sharpe
        
        # Add positive bias
        positive_returns = sample_returns + 0.01
        result = calculate_sharpe(positive_returns)
        
        assert result > 0
    
    def test_sharpe_negative_returns(self, sample_returns):
        """Test Sharpe with negative returns."""
        from polytrader.analytics.metrics import calculate_sharpe
        
        # Add negative bias
        negative_returns = sample_returns - 0.05
        result = calculate_sharpe(negative_returns)
        
        assert result < 0
    
    def test_sharpe_zero_volatility(self):
        """Test Sharpe with zero volatility."""
        from polytrader.analytics.metrics import calculate_sharpe
        
        # Constant returns = zero volatility
        constant_returns = pd.Series([0.01] * 100)
        result = calculate_sharpe(constant_returns)
        
        # Should handle gracefully (return 0 or inf)
        assert not np.isnan(result)


class TestCalculateSortino:
    """Tests for Sortino ratio calculation."""
    
    def test_sortino_basic(self, sample_returns):
        """Test basic Sortino calculation."""
        from polytrader.analytics.metrics import calculate_sortino
        
        result = calculate_sortino(sample_returns)
        
        assert isinstance(result, float)
    
    def test_sortino_no_downside(self):
        """Test Sortino with no downside."""
        from polytrader.analytics.metrics import calculate_sortino
        
        # All positive returns
        positive_returns = pd.Series([0.01, 0.02, 0.015, 0.01, 0.025])
        result = calculate_sortino(positive_returns)
        
        # Should be infinity or very high
        assert result > 0 or result == float("inf")


class TestCalculateMaxDrawdown:
    """Tests for max drawdown calculation."""
    
    def test_drawdown_empty(self):
        """Test drawdown with empty data."""
        from polytrader.analytics.metrics import calculate_max_drawdown
        
        result = calculate_max_drawdown(pd.Series(dtype=float))
        
        assert result["max_drawdown"] == 0.0
        assert result["max_drawdown_pct"] == 0.0
    
    def test_drawdown_with_equity(self, sample_equity_curve):
        """Test drawdown calculation."""
        from polytrader.analytics.metrics import calculate_max_drawdown
        
        result = calculate_max_drawdown(sample_equity_curve)
        
        assert "max_drawdown" in result
        assert "max_drawdown_pct" in result
        assert result["max_drawdown"] <= 0  # Drawdown is negative
        assert result["max_drawdown_pct"] <= 0
    
    def test_drawdown_no_drawdown(self):
        """Test with monotonically increasing equity."""
        from polytrader.analytics.metrics import calculate_max_drawdown
        
        # Always increasing
        equity = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "equity": range(100, 110)
        })
        
        result = calculate_max_drawdown(equity)
        
        assert result["max_drawdown"] == 0.0


class TestCalculateWinRate:
    """Tests for win rate calculation."""
    
    def test_win_rate_empty(self):
        """Test win rate with no trades."""
        from polytrader.analytics.metrics import calculate_win_rate
        
        result = calculate_win_rate([])
        
        assert result["win_rate"] == 0.0
        assert result["wins"] == 0
        assert result["losses"] == 0
    
    def test_win_rate_with_trades(self, sample_trades):
        """Test win rate calculation."""
        from polytrader.analytics.metrics import calculate_win_rate
        
        result = calculate_win_rate(sample_trades)
        
        assert 0 <= result["win_rate"] <= 1
        assert result["wins"] + result["losses"] >= 0


class TestCalculateProfitFactor:
    """Tests for profit factor calculation."""
    
    def test_profit_factor_empty(self):
        """Test profit factor with no trades."""
        from polytrader.analytics.metrics import calculate_profit_factor
        
        result = calculate_profit_factor([])
        
        assert result == 0.0
    
    def test_profit_factor_with_trades(self, sample_trades):
        """Test profit factor calculation."""
        from polytrader.analytics.metrics import calculate_profit_factor
        
        result = calculate_profit_factor(sample_trades)
        
        assert result >= 0


class TestCalculateExpectancy:
    """Tests for expectancy calculation."""
    
    def test_expectancy_empty(self):
        """Test expectancy with no trades."""
        from polytrader.analytics.metrics import calculate_expectancy
        
        result = calculate_expectancy([])
        
        assert result == 0.0
    
    def test_expectancy_with_trades(self, sample_trades):
        """Test expectancy calculation."""
        from polytrader.analytics.metrics import calculate_expectancy
        
        result = calculate_expectancy(sample_trades)
        
        assert isinstance(result, float)


class TestBuildEquityCurve:
    """Tests for equity curve building."""
    
    def test_equity_curve_empty(self):
        """Test equity curve with no trades."""
        from polytrader.analytics.metrics import build_equity_curve
        
        result = build_equity_curve([], starting_balance=10000)
        
        assert len(result) == 0
    
    def test_equity_curve_with_trades(self, sample_trades):
        """Test equity curve building."""
        from polytrader.analytics.metrics import build_equity_curve
        
        result = build_equity_curve(sample_trades, starting_balance=10000)
        
        assert "date" in result.columns
        assert "equity" in result.columns


class TestCalculateAllMetrics:
    """Tests for comprehensive metrics calculation."""
    
    def test_all_metrics_empty(self):
        """Test all metrics with no trades."""
        from polytrader.analytics.metrics import calculate_all_metrics
        
        result = calculate_all_metrics([])
        
        assert "total_pnl" in result
        assert "win_rate" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown_pct" in result
    
    def test_all_metrics_with_trades(self, sample_trades):
        """Test all metrics calculation."""
        from polytrader.analytics.metrics import calculate_all_metrics
        
        result = calculate_all_metrics(sample_trades)
        
        # Check all expected keys
        expected_keys = [
            "total_pnl", "gross_profit", "gross_loss", "num_trades",
            "win_rate", "wins", "losses", "avg_win", "avg_loss",
            "sharpe_ratio", "sortino_ratio", "max_drawdown", "max_drawdown_pct",
            "profit_factor", "expectancy"
        ]
        
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

