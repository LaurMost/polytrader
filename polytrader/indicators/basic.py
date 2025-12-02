"""
Basic technical indicators for strategy development.
"""

from typing import Optional, Union

import numpy as np
import pandas as pd


def sma(data: Union[pd.Series, list], period: int) -> pd.Series:
    """
    Simple Moving Average.
    
    Args:
        data: Price series
        period: Number of periods
        
    Returns:
        SMA series
    """
    series = pd.Series(data) if isinstance(data, list) else data
    return series.rolling(window=period).mean()


def ema(data: Union[pd.Series, list], period: int) -> pd.Series:
    """
    Exponential Moving Average.
    
    Args:
        data: Price series
        period: Number of periods
        
    Returns:
        EMA series
    """
    series = pd.Series(data) if isinstance(data, list) else data
    return series.ewm(span=period, adjust=False).mean()


def rsi(data: Union[pd.Series, list], period: int = 14) -> pd.Series:
    """
    Relative Strength Index.
    
    Args:
        data: Price series
        period: Number of periods (default 14)
        
    Returns:
        RSI series (0-100)
    """
    series = pd.Series(data) if isinstance(data, list) else data
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def bollinger_bands(
    data: Union[pd.Series, list],
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.
    
    Args:
        data: Price series
        period: Number of periods (default 20)
        std_dev: Standard deviation multiplier (default 2)
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    series = pd.Series(data) if isinstance(data, list) else data
    
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower


def macd(
    data: Union[pd.Series, list],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence.
    
    Args:
        data: Price series
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)
        
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    series = pd.Series(data) if isinstance(data, list) else data
    
    fast_ema = ema(series, fast_period)
    slow_ema = ema(series, slow_period)
    
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def momentum(data: Union[pd.Series, list], period: int = 10) -> pd.Series:
    """
    Momentum indicator.
    
    Args:
        data: Price series
        period: Number of periods
        
    Returns:
        Momentum series
    """
    series = pd.Series(data) if isinstance(data, list) else data
    return series.diff(period)


def volatility(data: Union[pd.Series, list], period: int = 20) -> pd.Series:
    """
    Rolling volatility (standard deviation).
    
    Args:
        data: Price series
        period: Number of periods
        
    Returns:
        Volatility series
    """
    series = pd.Series(data) if isinstance(data, list) else data
    return series.rolling(window=period).std()


def rate_of_change(data: Union[pd.Series, list], period: int = 10) -> pd.Series:
    """
    Rate of Change (percentage).
    
    Args:
        data: Price series
        period: Number of periods
        
    Returns:
        ROC series
    """
    series = pd.Series(data) if isinstance(data, list) else data
    return series.pct_change(periods=period) * 100


def stochastic(
    high: Union[pd.Series, list],
    low: Union[pd.Series, list],
    close: Union[pd.Series, list],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        k_period: %K period (default 14)
        d_period: %D period (default 3)
        
    Returns:
        Tuple of (%K, %D)
    """
    high_s = pd.Series(high) if isinstance(high, list) else high
    low_s = pd.Series(low) if isinstance(low, list) else low
    close_s = pd.Series(close) if isinstance(close, list) else close
    
    lowest_low = low_s.rolling(window=k_period).min()
    highest_high = high_s.rolling(window=k_period).max()
    
    k = 100 * (close_s - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    
    return k, d


def atr(
    high: Union[pd.Series, list],
    low: Union[pd.Series, list],
    close: Union[pd.Series, list],
    period: int = 14,
) -> pd.Series:
    """
    Average True Range.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: Number of periods (default 14)
        
    Returns:
        ATR series
    """
    high_s = pd.Series(high) if isinstance(high, list) else high
    low_s = pd.Series(low) if isinstance(low, list) else low
    close_s = pd.Series(close) if isinstance(close, list) else close
    
    prev_close = close_s.shift(1)
    
    tr1 = high_s - low_s
    tr2 = abs(high_s - prev_close)
    tr3 = abs(low_s - prev_close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return tr.rolling(window=period).mean()


def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    Detect crossover (series1 crosses above series2).
    
    Args:
        series1: First series
        series2: Second series
        
    Returns:
        Boolean series (True where crossover occurs)
    """
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    Detect crossunder (series1 crosses below series2).
    
    Args:
        series1: First series
        series2: Second series
        
    Returns:
        Boolean series (True where crossunder occurs)
    """
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))
