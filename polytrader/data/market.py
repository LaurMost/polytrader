"""
Market data fetching utilities.
"""

from typing import Optional

import pandas as pd

from polytrader.core.client import PolymarketClient
from polytrader.data.models import Market
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


class MarketDataFetcher:
    """
    Utility class for fetching market data.
    
    Usage:
        fetcher = MarketDataFetcher()
        
        # Get market info
        market = fetcher.get_market("https://polymarket.com/event/...")
        
        # Get price history
        df = fetcher.get_price_history(market)
    """

    def __init__(self):
        """Initialize the fetcher."""
        self.client = PolymarketClient()

    def get_market(self, market_ref: str) -> Optional[Market]:
        """
        Get market by URL, slug, or ID.
        
        Args:
            market_ref: Market URL, slug, or ID
            
        Returns:
            Market object or None
        """
        from polytrader.utils.url_parser import (
            get_market_from_url,
            is_valid_polymarket_url,
        )
        
        if is_valid_polymarket_url(market_ref):
            return get_market_from_url(market_ref)
        elif "/" in market_ref:
            return self.client.get_market_by_slug(market_ref)
        else:
            return self.client.get_market_by_id(market_ref)

    def get_price_history(
        self,
        market: Market,
        outcome: str = "YES",
        interval: str = "max",
        fidelity: int = 1440,
    ) -> pd.DataFrame:
        """
        Get price history for a market.
        
        Args:
            market: Market object
            outcome: "YES" or "NO"
            interval: Time interval (1h, 6h, 1d, 1w, 1m, max)
            fidelity: Resolution in minutes
            
        Returns:
            DataFrame with columns: timestamp, price
        """
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        
        history = self.client.get_price_history(
            token_id=token_id,
            interval=interval,
            fidelity=fidelity,
        )
        
        if not history:
            return pd.DataFrame(columns=["timestamp", "price"])
        
        df = pd.DataFrame(history)
        df["timestamp"] = pd.to_datetime(df["t"], unit="s")
        df["price"] = df["p"]
        
        return df[["timestamp", "price"]].sort_values("timestamp")

    def get_orderbook(self, market: Market, outcome: str = "YES") -> dict:
        """
        Get orderbook for a market.
        
        Args:
            market: Market object
            outcome: "YES" or "NO"
            
        Returns:
            Orderbook dict with bids and asks
        """
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        return self.client.get_orderbook(token_id) or {"bids": [], "asks": []}

    def get_spread(self, market: Market, outcome: str = "YES") -> Optional[dict]:
        """
        Get bid-ask spread for a market.
        
        Args:
            market: Market object
            outcome: "YES" or "NO"
            
        Returns:
            Spread dict with bid, ask, spread
        """
        token_id = market.token_id_yes if outcome == "YES" else market.token_id_no
        return self.client.get_spread(token_id)

    def get_markets(
        self,
        closed: bool = False,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> list[Market]:
        """
        Get list of markets.
        
        Args:
            closed: Include closed markets
            limit: Maximum number of markets
            category: Filter by category
            
        Returns:
            List of Market objects
        """
        markets = self.client.get_markets(closed=closed, limit=limit)
        
        if category:
            markets = [m for m in markets if m.category == category]
        
        return markets

    def search_markets(self, query: str, limit: int = 20) -> list[Market]:
        """
        Search for markets by query.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching markets
        """
        # Simple search by checking if query is in question
        markets = self.client.get_markets(limit=500)
        query_lower = query.lower()
        
        matches = [
            m for m in markets
            if query_lower in m.question.lower()
        ]
        
        return matches[:limit]

