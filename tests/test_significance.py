"""
Tests for polytrader.analytics.significance module.
"""

import pytest
import numpy as np
import pandas as pd


class TestTTestReturns:
    """Tests for t-test on returns."""
    
    def test_t_test_empty(self):
        """Test t-test with empty returns."""
        from polytrader.analytics.significance import t_test_returns
        
        result = t_test_returns(pd.Series(dtype=float))
        
        assert result["p_value"] == 1.0
        assert result["is_significant"] == False
    
    def test_t_test_basic(self, sample_returns):
        """Test basic t-test calculation."""
        from polytrader.analytics.significance import t_test_returns
        
        result = t_test_returns(sample_returns)
        
        assert "t_statistic" in result
        assert "p_value" in result
        assert "is_significant" in result
        assert "mean" in result
        assert "std_error" in result
    
    def test_t_test_significant_positive(self):
        """Test t-test with significantly positive returns."""
        from polytrader.analytics.significance import t_test_returns
        
        # Strong positive returns
        returns = pd.Series([0.05, 0.06, 0.04, 0.07, 0.05] * 20)
        result = t_test_returns(returns)
        
        assert result["t_statistic"] > 0
        assert result["is_significant"] == True
        assert result["p_value"] < 0.05
    
    def test_t_test_not_significant(self):
        """Test t-test with non-significant returns."""
        from polytrader.analytics.significance import t_test_returns
        
        # Random returns around zero
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0, 0.01, 20))
        result = t_test_returns(returns)
        
        # May or may not be significant with small sample
        assert "p_value" in result
    
    def test_t_test_single_value(self):
        """Test t-test with single value."""
        from polytrader.analytics.significance import t_test_returns
        
        result = t_test_returns(pd.Series([0.01]))
        
        assert result["sample_size"] == 1


class TestBootstrapConfidenceInterval:
    """Tests for bootstrap confidence intervals."""
    
    def test_bootstrap_empty(self):
        """Test bootstrap with empty returns."""
        from polytrader.analytics.significance import bootstrap_confidence_interval
        
        result = bootstrap_confidence_interval(pd.Series(dtype=float))
        
        assert result["lower_bound"] == 0.0
        assert result["upper_bound"] == 0.0
    
    def test_bootstrap_basic(self, sample_returns):
        """Test basic bootstrap calculation."""
        from polytrader.analytics.significance import bootstrap_confidence_interval
        
        result = bootstrap_confidence_interval(sample_returns)
        
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "point_estimate" in result
        assert "confidence_level" in result
    
    def test_bootstrap_confidence_level(self, sample_returns):
        """Test bootstrap with different confidence levels."""
        from polytrader.analytics.significance import bootstrap_confidence_interval
        
        result_95 = bootstrap_confidence_interval(sample_returns, confidence_level=0.95)
        result_99 = bootstrap_confidence_interval(sample_returns, confidence_level=0.99)
        
        # 99% CI should be wider than 95% CI
        width_95 = result_95["upper_bound"] - result_95["lower_bound"]
        width_99 = result_99["upper_bound"] - result_99["lower_bound"]
        
        assert width_99 >= width_95
    
    def test_bootstrap_mean_statistic(self, sample_returns):
        """Test bootstrap with mean statistic."""
        from polytrader.analytics.significance import bootstrap_confidence_interval
        
        result = bootstrap_confidence_interval(sample_returns, statistic="mean")
        
        # Point estimate should be close to actual mean
        actual_mean = sample_returns.mean()
        assert abs(result["point_estimate"] - actual_mean) < 0.01
    
    def test_bootstrap_sharpe_statistic(self, sample_returns):
        """Test bootstrap with Sharpe ratio statistic."""
        from polytrader.analytics.significance import bootstrap_confidence_interval
        
        result = bootstrap_confidence_interval(sample_returns, statistic="sharpe")
        
        assert "lower_bound" in result
        assert "upper_bound" in result


class TestRequiredTradesForSignificance:
    """Tests for required sample size calculation."""
    
    def test_required_trades_basic(self):
        """Test basic sample size calculation."""
        from polytrader.analytics.significance import required_trades_for_significance
        
        result = required_trades_for_significance(win_rate=0.55)
        
        assert result > 0
        assert isinstance(result, int)
    
    def test_required_trades_high_win_rate(self):
        """Test sample size with high win rate."""
        from polytrader.analytics.significance import required_trades_for_significance
        
        result_low = required_trades_for_significance(win_rate=0.55)
        result_high = required_trades_for_significance(win_rate=0.90)
        
        # Higher win rate needs fewer samples (more decisive)
        assert result_high < result_low
    
    def test_required_trades_confidence_level(self):
        """Test sample size with different confidence levels."""
        from polytrader.analytics.significance import required_trades_for_significance
        
        result_95 = required_trades_for_significance(win_rate=0.55, confidence_level=0.95)
        result_99 = required_trades_for_significance(win_rate=0.55, confidence_level=0.99)
        
        # Higher confidence needs more samples
        assert result_99 > result_95
    
    def test_required_trades_margin_of_error(self):
        """Test sample size with different margins of error."""
        from polytrader.analytics.significance import required_trades_for_significance
        
        result_5pct = required_trades_for_significance(win_rate=0.55, margin_of_error=0.05)
        result_10pct = required_trades_for_significance(win_rate=0.55, margin_of_error=0.10)
        
        # Smaller margin needs more samples
        assert result_5pct > result_10pct


class TestCalculateStatisticalSummary:
    """Tests for comprehensive statistical summary."""
    
    def test_summary_empty(self):
        """Test summary with empty returns."""
        from polytrader.analytics.significance import calculate_statistical_summary
        
        result = calculate_statistical_summary(pd.Series(dtype=float))
        
        assert "t_statistic" in result
        assert "p_value" in result
        assert "is_significant" in result
    
    def test_summary_basic(self, sample_returns):
        """Test basic statistical summary."""
        from polytrader.analytics.significance import calculate_statistical_summary
        
        result = calculate_statistical_summary(sample_returns)
        
        expected_keys = [
            "t_statistic", "p_value", "is_significant", "significance_level",
            "mean_ci_lower", "mean_ci_upper", "sharpe_ci_lower", "sharpe_ci_upper",
            "sample_size", "mean_return", "std_return", "skewness", "kurtosis",
            "required_trades", "has_sufficient_data", "data_sufficiency_pct"
        ]
        
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
    
    def test_summary_significance_levels(self):
        """Test significance level descriptions."""
        from polytrader.analytics.significance import calculate_statistical_summary
        
        # Very significant returns
        significant_returns = pd.Series([0.05, 0.06, 0.04, 0.07, 0.05] * 20)
        result = calculate_statistical_summary(significant_returns)
        
        assert "Strong" in result["significance_level"] or "Very Strong" in result["significance_level"]
    
    def test_summary_data_sufficiency(self, sample_returns):
        """Test data sufficiency calculation."""
        from polytrader.analytics.significance import calculate_statistical_summary
        
        result = calculate_statistical_summary(sample_returns)
        
        assert result["sample_size"] == len(sample_returns)
        assert 0 <= result["data_sufficiency_pct"] <= 100

