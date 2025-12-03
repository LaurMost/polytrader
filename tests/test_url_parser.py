"""
Tests for polytrader.utils.url_parser module.
"""

import pytest


class TestParseMarketUrl:
    """Tests for URL parsing."""
    
    def test_parse_event_url(self):
        """Test parsing event URL."""
        from polytrader.utils.url_parser import parse_market_url
        
        url = "https://polymarket.com/event/bitcoin-100k"
        result = parse_market_url(url)
        
        assert result is not None
        assert result["slug"] == "bitcoin-100k"
        assert result["type"] == "event"
    
    def test_parse_market_url(self):
        """Test parsing market URL."""
        from polytrader.utils.url_parser import parse_market_url
        
        url = "https://polymarket.com/market/bitcoin-100k-yes"
        result = parse_market_url(url)
        
        assert result is not None
        assert "slug" in result
    
    def test_parse_url_with_query_params(self):
        """Test parsing URL with query parameters."""
        from polytrader.utils.url_parser import parse_market_url
        
        url = "https://polymarket.com/event/bitcoin-100k?tid=123"
        result = parse_market_url(url)
        
        assert result is not None
        assert result["slug"] == "bitcoin-100k"
        assert result["tid"] == "123"
    
    def test_parse_invalid_url(self):
        """Test parsing invalid URL."""
        from polytrader.utils.url_parser import parse_market_url
        
        url = "https://example.com/not-polymarket"
        result = parse_market_url(url)
        
        # Should return dict with None values for invalid URLs
        assert result["slug"] is None
        assert result["type"] is None
    
    def test_parse_empty_url(self):
        """Test parsing empty URL."""
        from polytrader.utils.url_parser import parse_market_url
        
        result = parse_market_url("")
        
        assert result["slug"] is None


class TestIsValidPolymarketUrl:
    """Tests for URL validation."""
    
    def test_valid_polymarket_url(self):
        """Test valid Polymarket URL."""
        from polytrader.utils.url_parser import is_valid_polymarket_url
        
        assert is_valid_polymarket_url("https://polymarket.com/event/test")
        assert is_valid_polymarket_url("https://www.polymarket.com/event/test")
    
    def test_invalid_domain(self):
        """Test invalid domain."""
        from polytrader.utils.url_parser import is_valid_polymarket_url
        
        assert not is_valid_polymarket_url("https://example.com/event/test")
        assert not is_valid_polymarket_url("https://polymarket.org/event/test")
    
    def test_invalid_url_format(self):
        """Test invalid URL format."""
        from polytrader.utils.url_parser import is_valid_polymarket_url
        
        assert not is_valid_polymarket_url("not-a-url")
        assert not is_valid_polymarket_url("")
        assert not is_valid_polymarket_url(None)


class TestExtractSlug:
    """Tests for extracting slug from URL."""
    
    def test_extract_slug(self):
        """Test extracting slug."""
        from polytrader.utils.url_parser import extract_slug_from_url
        
        url = "https://polymarket.com/event/bitcoin-100k"
        result = extract_slug_from_url(url)
        
        assert result == "bitcoin-100k"
    
    def test_extract_slug_empty(self):
        """Test extracting slug from empty URL."""
        from polytrader.utils.url_parser import extract_slug_from_url
        
        result = extract_slug_from_url("")
        
        assert result is None


class TestFormatMarketSummary:
    """Tests for market summary formatting."""
    
    def test_format_summary(self):
        """Test formatting market summary."""
        from polytrader.utils.url_parser import format_market_summary
        from polytrader.data.models import Market
        
        market = Market(
            id="test_market_123",
            condition_id="cond_123",
            question="Will Bitcoin reach $100k by end of 2024?",
            slug="bitcoin-100k-2024",
            token_id_yes="token_yes_123",
            token_id_no="token_no_123",
            price_yes=0.65,
            price_no=0.35,
            volume=1000000.0,
            liquidity=500000.0,
            closed=False,
        )
        
        result = format_market_summary(market)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain key information
        assert "Bitcoin" in result or "100k" in result

