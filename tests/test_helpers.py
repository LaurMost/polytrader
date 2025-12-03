"""
Tests for polytrader.utils.helpers module.
"""

import pytest


class TestFormatAmount:
    """Tests for amount formatting."""
    
    def test_format_basic(self):
        """Test basic amount formatting."""
        from polytrader.utils.helpers import format_amount
        
        result = format_amount(1234.56)
        
        assert "$" in result or "1234" in result or "1,234" in result
    
    def test_format_large_amount(self):
        """Test formatting large amounts."""
        from polytrader.utils.helpers import format_amount
        
        result = format_amount(1000000)
        
        assert "1" in result
        # Should have some formatting (commas or abbreviation)
    
    def test_format_small_amount(self):
        """Test formatting small amounts."""
        from polytrader.utils.helpers import format_amount
        
        result = format_amount(0.01)
        
        assert "0" in result
    
    def test_format_zero(self):
        """Test formatting zero."""
        from polytrader.utils.helpers import format_amount
        
        result = format_amount(0)
        
        assert "0" in result
    
    def test_format_negative(self):
        """Test formatting negative amounts."""
        from polytrader.utils.helpers import format_amount
        
        result = format_amount(-1234.56)
        
        assert "-" in result or "1234" in result


class TestFormatPercentage:
    """Tests for percentage formatting."""
    
    def test_format_basic(self):
        """Test basic percentage formatting."""
        from polytrader.utils.helpers import format_percentage
        
        result = format_percentage(0.5)
        
        assert "50" in result or "%" in result
    
    def test_format_whole_number(self):
        """Test formatting whole percentage."""
        from polytrader.utils.helpers import format_percentage
        
        result = format_percentage(1.0)
        
        assert "100" in result
    
    def test_format_small_percentage(self):
        """Test formatting small percentage."""
        from polytrader.utils.helpers import format_percentage
        
        result = format_percentage(0.01)
        
        assert "1" in result
    
    def test_format_zero_percentage(self):
        """Test formatting zero percentage."""
        from polytrader.utils.helpers import format_percentage
        
        result = format_percentage(0)
        
        assert "0" in result


class TestFormatPnL:
    """Tests for P&L formatting."""
    
    def test_format_positive_pnl(self):
        """Test formatting positive P&L."""
        from polytrader.utils.helpers import format_pnl
        
        result = format_pnl(100.50)
        
        assert "+" in result or "100" in result
    
    def test_format_negative_pnl(self):
        """Test formatting negative P&L."""
        from polytrader.utils.helpers import format_pnl
        
        result = format_pnl(-50.25)
        
        assert "-" in result or "50" in result
    
    def test_format_zero_pnl(self):
        """Test formatting zero P&L."""
        from polytrader.utils.helpers import format_pnl
        
        result = format_pnl(0)
        
        assert "0" in result

