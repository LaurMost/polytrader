"""
Statistical significance tests for trading strategies.

Provides t-tests, bootstrap confidence intervals, and sample size calculations
to determine if a strategy has a statistically significant edge.
"""

import math
from typing import Optional, Union

import numpy as np
import pandas as pd


def t_test_returns(
    returns: Union[pd.Series, list, np.ndarray],
    null_hypothesis: float = 0.0,
) -> dict:
    """
    Perform one-sample t-test on returns.
    
    Tests if mean return is significantly different from null_hypothesis.
    
    Args:
        returns: Series of returns
        null_hypothesis: Expected return under null (default 0)
        
    Returns:
        Dict with t_statistic, p_value, is_significant, mean, std_error
    """
    if isinstance(returns, (list, np.ndarray)):
        returns = pd.Series(returns)
    
    # Remove NaN values
    returns = returns.dropna()
    
    n = len(returns)
    
    if n < 2:
        return {
            "t_statistic": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "mean": 0.0,
            "std_error": 0.0,
            "sample_size": n,
            "degrees_of_freedom": 0,
        }
    
    mean = returns.mean()
    std = returns.std(ddof=1)  # Sample standard deviation
    std_error = std / np.sqrt(n)
    
    if std_error == 0:
        return {
            "t_statistic": float("inf") if mean != null_hypothesis else 0.0,
            "p_value": 0.0 if mean != null_hypothesis else 1.0,
            "is_significant": mean != null_hypothesis,
            "mean": float(mean),
            "std_error": 0.0,
            "sample_size": n,
            "degrees_of_freedom": n - 1,
        }
    
    # Calculate t-statistic
    t_stat = (mean - null_hypothesis) / std_error
    
    # Calculate p-value using t-distribution
    # Two-tailed test
    df = n - 1
    p_value = _t_distribution_p_value(t_stat, df)
    
    return {
        "t_statistic": float(t_stat),
        "p_value": float(p_value),
        "is_significant": p_value < 0.05,
        "mean": float(mean),
        "std_error": float(std_error),
        "sample_size": n,
        "degrees_of_freedom": df,
    }


def _t_distribution_p_value(t_stat: float, df: int) -> float:
    """
    Calculate two-tailed p-value from t-statistic.
    
    Uses approximation for t-distribution CDF.
    """
    try:
        from scipy import stats
        return float(2 * (1 - stats.t.cdf(abs(t_stat), df)))
    except ImportError:
        # Fallback approximation using normal distribution for large df
        if df > 30:
            # Use normal approximation
            return 2 * (1 - _normal_cdf(abs(t_stat)))
        else:
            # Simple approximation
            # This is rough but works for basic significance testing
            z = abs(t_stat)
            if z > 3.5:
                return 0.001
            elif z > 2.5:
                return 0.02
            elif z > 2.0:
                return 0.05
            elif z > 1.5:
                return 0.15
            else:
                return 0.3


def _normal_cdf(x: float) -> float:
    """Approximation of standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bootstrap_confidence_interval(
    returns: Union[pd.Series, list, np.ndarray],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    statistic: str = "mean",
) -> dict:
    """
    Calculate bootstrap confidence interval for returns.
    
    Args:
        returns: Series of returns
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level (default 0.95 for 95% CI)
        statistic: Statistic to calculate ("mean", "median", "sharpe")
        
    Returns:
        Dict with lower_bound, upper_bound, point_estimate, confidence_level
    """
    if isinstance(returns, (list, np.ndarray)):
        returns = np.array(returns)
    else:
        returns = returns.dropna().values
    
    n = len(returns)
    
    if n < 2:
        return {
            "lower_bound": 0.0,
            "upper_bound": 0.0,
            "point_estimate": 0.0,
            "confidence_level": confidence_level,
            "n_samples": n,
        }
    
    # Calculate statistic function
    if statistic == "mean":
        stat_func = np.mean
    elif statistic == "median":
        stat_func = np.median
    elif statistic == "sharpe":
        def stat_func(x):
            if np.std(x) == 0:
                return 0.0
            return np.mean(x) / np.std(x) * np.sqrt(252)
    else:
        stat_func = np.mean
    
    # Point estimate
    point_estimate = stat_func(returns)
    
    # Bootstrap resampling
    np.random.seed(42)  # For reproducibility
    bootstrap_stats = []
    
    for _ in range(n_bootstrap):
        # Sample with replacement
        sample = np.random.choice(returns, size=n, replace=True)
        bootstrap_stats.append(stat_func(sample))
    
    bootstrap_stats = np.array(bootstrap_stats)
    
    # Calculate percentiles for confidence interval
    alpha = 1 - confidence_level
    lower_percentile = alpha / 2 * 100
    upper_percentile = (1 - alpha / 2) * 100
    
    lower_bound = np.percentile(bootstrap_stats, lower_percentile)
    upper_bound = np.percentile(bootstrap_stats, upper_percentile)
    
    return {
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "point_estimate": float(point_estimate),
        "confidence_level": confidence_level,
        "n_samples": n,
        "std_error": float(np.std(bootstrap_stats)),
    }


def required_trades_for_significance(
    win_rate: float,
    confidence_level: float = 0.95,
    margin_of_error: float = 0.05,
) -> int:
    """
    Calculate minimum number of trades needed for statistical significance.
    
    Uses sample size formula for proportions.
    
    Args:
        win_rate: Estimated win rate (0-1)
        confidence_level: Desired confidence level
        margin_of_error: Acceptable margin of error
        
    Returns:
        Minimum number of trades required
    """
    # Z-score for confidence level
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    
    z = z_scores.get(confidence_level, 1.96)
    
    # Sample size formula for proportions
    # n = (z^2 * p * (1-p)) / e^2
    p = win_rate
    e = margin_of_error
    
    if e == 0:
        return float("inf")
    
    n = (z ** 2 * p * (1 - p)) / (e ** 2)
    
    return int(np.ceil(n))


def calculate_statistical_summary(
    returns: Union[pd.Series, list, np.ndarray],
    trades: Optional[list] = None,
) -> dict:
    """
    Calculate comprehensive statistical summary.
    
    Args:
        returns: Series of returns
        trades: Optional list of Trade objects
        
    Returns:
        Dict with all statistical metrics
    """
    if isinstance(returns, (list, np.ndarray)):
        returns = pd.Series(returns)
    
    returns = returns.dropna()
    
    # T-test
    t_test = t_test_returns(returns)
    
    # Bootstrap CI for mean return
    ci_mean = bootstrap_confidence_interval(returns, statistic="mean")
    
    # Bootstrap CI for Sharpe ratio
    ci_sharpe = bootstrap_confidence_interval(returns, statistic="sharpe")
    
    # Basic statistics
    n = len(returns)
    mean_return = returns.mean() if n > 0 else 0.0
    std_return = returns.std() if n > 0 else 0.0
    skewness = returns.skew() if n > 2 else 0.0
    kurtosis = returns.kurtosis() if n > 3 else 0.0
    
    # Required sample size (assuming current win rate)
    win_rate = (returns > 0).mean() if n > 0 else 0.5
    required_n = required_trades_for_significance(win_rate)
    
    # Significance interpretation
    if t_test["p_value"] < 0.01:
        significance_level = "Very Strong (p < 0.01)"
    elif t_test["p_value"] < 0.05:
        significance_level = "Strong (p < 0.05)"
    elif t_test["p_value"] < 0.10:
        significance_level = "Moderate (p < 0.10)"
    else:
        significance_level = "Not Significant (p >= 0.10)"
    
    return {
        # T-test results
        "t_statistic": t_test["t_statistic"],
        "p_value": t_test["p_value"],
        "is_significant": t_test["is_significant"],
        "significance_level": significance_level,
        
        # Confidence intervals
        "mean_ci_lower": ci_mean["lower_bound"],
        "mean_ci_upper": ci_mean["upper_bound"],
        "sharpe_ci_lower": ci_sharpe["lower_bound"],
        "sharpe_ci_upper": ci_sharpe["upper_bound"],
        
        # Basic statistics
        "sample_size": n,
        "mean_return": float(mean_return),
        "std_return": float(std_return),
        "skewness": float(skewness),
        "kurtosis": float(kurtosis),
        
        # Sample size analysis
        "required_trades": required_n,
        "has_sufficient_data": n >= required_n,
        "data_sufficiency_pct": min(n / required_n * 100, 100) if required_n > 0 else 100,
    }

