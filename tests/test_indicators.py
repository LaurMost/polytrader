"""
Tests for polytrader.indicators.basic module.
"""

import pytest
import numpy as np
import pandas as pd


class TestSMA:
    """Tests for Simple Moving Average."""
    
    def test_sma_basic(self, price_series):
        """Test basic SMA calculation."""
        from polytrader.indicators.basic import sma
        
        result = sma(price_series, period=10)
        
        assert len(result) == len(price_series)
        assert pd.isna(result.iloc[:9]).all()  # First 9 should be NaN
        assert not pd.isna(result.iloc[9])  # 10th should have value
    
    def test_sma_values(self):
        """Test SMA calculates correct values."""
        from polytrader.indicators.basic import sma
        
        prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = sma(prices, period=5)
        
        # SMA of [1,2,3,4,5] = 3.0
        assert result.iloc[4] == 3.0
        # SMA of [6,7,8,9,10] = 8.0
        assert result.iloc[9] == 8.0
    
    def test_sma_empty_series(self):
        """Test SMA with empty series."""
        from polytrader.indicators.basic import sma
        
        result = sma(pd.Series(dtype=float), period=10)
        
        assert len(result) == 0


class TestEMA:
    """Tests for Exponential Moving Average."""
    
    def test_ema_basic(self, price_series):
        """Test basic EMA calculation."""
        from polytrader.indicators.basic import ema
        
        result = ema(price_series, period=10)
        
        assert len(result) == len(price_series)
    
    def test_ema_responds_faster_than_sma(self, price_series):
        """Test that EMA responds faster to price changes than SMA."""
        from polytrader.indicators.basic import sma, ema
        
        # Create series with sudden jump
        prices = pd.Series([10] * 20 + [20] * 10)
        
        sma_result = sma(prices, period=10)
        ema_result = ema(prices, period=10)
        
        # After jump, EMA should be closer to new price than SMA
        assert ema_result.iloc[25] > sma_result.iloc[25]


class TestRSI:
    """Tests for Relative Strength Index."""
    
    def test_rsi_basic(self, price_series):
        """Test basic RSI calculation."""
        from polytrader.indicators.basic import rsi
        
        result = rsi(price_series, period=14)
        
        assert len(result) == len(price_series)
    
    def test_rsi_bounds(self, price_series):
        """Test RSI stays within 0-100 bounds."""
        from polytrader.indicators.basic import rsi
        
        result = rsi(price_series, period=14)
        valid_values = result.dropna()
        
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()
    
    def test_rsi_overbought(self):
        """Test RSI shows overbought for rising prices."""
        from polytrader.indicators.basic import rsi
        
        # Consistently rising prices
        prices = pd.Series(range(1, 101))
        result = rsi(prices, period=14)
        
        # Should show overbought (>70) for strong uptrend
        assert result.iloc[-1] > 70
    
    def test_rsi_oversold(self):
        """Test RSI shows oversold for falling prices."""
        from polytrader.indicators.basic import rsi
        
        # Consistently falling prices
        prices = pd.Series(range(100, 0, -1))
        result = rsi(prices, period=14)
        
        # Should show oversold (<30) for strong downtrend
        assert result.iloc[-1] < 30


class TestMACD:
    """Tests for MACD indicator."""
    
    def test_macd_basic(self, price_series):
        """Test basic MACD calculation."""
        from polytrader.indicators.basic import macd
        
        macd_line, signal_line, histogram = macd(price_series)
        
        assert len(macd_line) == len(price_series)
        assert len(signal_line) == len(price_series)
        assert len(histogram) == len(price_series)
    
    def test_macd_histogram_calculation(self, price_series):
        """Test MACD histogram is difference of MACD and signal."""
        from polytrader.indicators.basic import macd
        
        macd_line, signal_line, histogram = macd(price_series)
        
        # Histogram should equal MACD - Signal (where both are valid)
        valid_idx = ~(pd.isna(macd_line) | pd.isna(signal_line))
        
        np.testing.assert_array_almost_equal(
            histogram[valid_idx].values,
            (macd_line[valid_idx] - signal_line[valid_idx]).values,
            decimal=10
        )


class TestBollingerBands:
    """Tests for Bollinger Bands."""
    
    def test_bollinger_basic(self, price_series):
        """Test basic Bollinger Bands calculation."""
        from polytrader.indicators.basic import bollinger_bands
        
        upper, middle, lower = bollinger_bands(price_series, period=20)
        
        assert len(upper) == len(price_series)
        assert len(middle) == len(price_series)
        assert len(lower) == len(price_series)
    
    def test_bollinger_band_order(self, price_series):
        """Test Bollinger Bands maintain proper order."""
        from polytrader.indicators.basic import bollinger_bands
        
        upper, middle, lower = bollinger_bands(price_series, period=20)
        
        # Upper > Middle > Lower (where valid)
        valid_idx = ~(pd.isna(upper) | pd.isna(middle) | pd.isna(lower))
        
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()
    
    def test_bollinger_middle_is_sma(self, price_series):
        """Test middle band equals SMA."""
        from polytrader.indicators.basic import bollinger_bands, sma
        
        upper, middle, lower = bollinger_bands(price_series, period=20)
        sma_result = sma(price_series, period=20)
        
        # Middle band should equal SMA
        valid_idx = ~pd.isna(middle)
        
        np.testing.assert_array_almost_equal(
            middle[valid_idx].values,
            sma_result[valid_idx].values,
            decimal=10
        )


class TestATR:
    """Tests for Average True Range."""
    
    def test_atr_basic(self, ohlcv_data):
        """Test basic ATR calculation."""
        from polytrader.indicators.basic import atr
        
        result = atr(
            ohlcv_data['high'],
            ohlcv_data['low'],
            ohlcv_data['close'],
            period=14
        )
        
        assert len(result) == len(ohlcv_data)
    
    def test_atr_positive(self, ohlcv_data):
        """Test ATR is always positive."""
        from polytrader.indicators.basic import atr
        
        result = atr(
            ohlcv_data['high'],
            ohlcv_data['low'],
            ohlcv_data['close'],
            period=14
        )
        
        valid_values = result.dropna()
        assert (valid_values >= 0).all()


class TestROC:
    """Tests for Rate of Change."""
    
    def test_roc_basic(self, price_series):
        """Test basic ROC calculation."""
        from polytrader.indicators.basic import roc
        
        result = roc(price_series, period=10)
        
        assert len(result) == len(price_series)
    
    def test_roc_values(self):
        """Test ROC calculates correct values."""
        from polytrader.indicators.basic import roc
        
        # 100% increase
        prices = pd.Series([100] * 10 + [200])
        result = roc(prices, period=10)
        
        # ROC = (200 - 100) / 100 * 100 = 100%
        assert abs(result.iloc[-1] - 100.0) < 0.01


class TestOBV:
    """Tests for On-Balance Volume."""
    
    def test_obv_basic(self, ohlcv_data):
        """Test basic OBV calculation."""
        from polytrader.indicators.basic import obv
        
        result = obv(ohlcv_data['close'], ohlcv_data['volume'])
        
        assert len(result) == len(ohlcv_data)
    
    def test_obv_direction(self):
        """Test OBV increases on up days, decreases on down days."""
        from polytrader.indicators.basic import obv
        
        close = pd.Series([100, 101, 100])  # Up, then down
        volume = pd.Series([1000, 1000, 1000])
        
        result = obv(close, volume)
        
        # OBV should increase then decrease
        assert result.iloc[1] > result.iloc[0]  # Up day
        assert result.iloc[2] < result.iloc[1]  # Down day

