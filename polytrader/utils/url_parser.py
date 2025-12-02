"""
URL parser for Polymarket market URLs.

Extracts market information from Polymarket URLs and fetches full market details.
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

from polytrader.data.models import Market
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


def parse_market_url(url: str) -> dict:
    """
    Parse a Polymarket URL and extract identifiers.
    
    Supports URLs like:
    - https://polymarket.com/event/fed-decision-in-october
    - https://polymarket.com/event/fed-decision-in-october?tid=1758818660485
    - https://polymarket.com/market/will-bitcoin-reach-100k
    
    Args:
        url: Polymarket URL
        
    Returns:
        Dictionary with parsed components:
        - type: "event" or "market"
        - slug: The URL slug
        - tid: Transaction ID if present
        - raw_url: Original URL
    """
    result = {
        "type": None,
        "slug": None,
        "tid": None,
        "raw_url": url,
    }
    
    try:
        parsed = urlparse(url)
        
        # Extract path components
        path_parts = [p for p in parsed.path.split("/") if p]
        
        if len(path_parts) >= 2:
            if path_parts[0] == "event":
                result["type"] = "event"
                result["slug"] = path_parts[1]
            elif path_parts[0] == "market":
                result["type"] = "market"
                result["slug"] = path_parts[1]
        
        # Extract query parameters
        query_params = parse_qs(parsed.query)
        if "tid" in query_params:
            result["tid"] = query_params["tid"][0]
        
    except Exception as e:
        logger.error(f"Failed to parse URL: {e}")
    
    return result


def get_market_from_url(url: str) -> Optional[Market]:
    """
    Fetch full market details from a Polymarket URL.
    
    Args:
        url: Polymarket URL
        
    Returns:
        Market object with full details, or None if not found
    """
    from polytrader.core.client import PolymarketClient
    
    parsed = parse_market_url(url)
    
    if not parsed["slug"]:
        logger.error(f"Could not extract slug from URL: {url}")
        return None
    
    client = PolymarketClient()
    
    if parsed["type"] == "event":
        # Fetch event and get first market
        event_data = client.get_event(parsed["slug"])
        if event_data and "markets" in event_data and event_data["markets"]:
            # Return the first market from the event
            market_data = event_data["markets"][0]
            return client._parse_market(market_data)
    
    elif parsed["type"] == "market":
        return client.get_market_by_slug(parsed["slug"])
    
    return None


def get_all_markets_from_event_url(url: str) -> list[Market]:
    """
    Fetch all markets from an event URL.
    
    Args:
        url: Polymarket event URL
        
    Returns:
        List of Market objects
    """
    from polytrader.core.client import PolymarketClient
    
    parsed = parse_market_url(url)
    
    if not parsed["slug"] or parsed["type"] != "event":
        logger.error(f"Invalid event URL: {url}")
        return []
    
    client = PolymarketClient()
    event_data = client.get_event(parsed["slug"])
    
    if not event_data or "markets" not in event_data:
        return []
    
    markets = []
    for market_data in event_data["markets"]:
        market = client._parse_market(market_data)
        if market:
            markets.append(market)
    
    return markets


def extract_slug_from_url(url: str) -> Optional[str]:
    """
    Extract just the slug from a Polymarket URL.
    
    Args:
        url: Polymarket URL
        
    Returns:
        Slug string or None
    """
    parsed = parse_market_url(url)
    return parsed.get("slug")


def is_valid_polymarket_url(url: str) -> bool:
    """
    Check if a URL is a valid Polymarket URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if valid Polymarket URL
    """
    try:
        parsed = urlparse(url)
        
        # Check domain
        if "polymarket.com" not in parsed.netloc:
            return False
        
        # Check path
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) < 2:
            return False
        
        if path_parts[0] not in ("event", "market"):
            return False
        
        return True
        
    except Exception:
        return False


def format_market_summary(market: Market) -> str:
    """
    Format a market summary for display.
    
    Args:
        market: Market object
        
    Returns:
        Formatted string summary
    """
    lines = [
        f"Market: {market.question}",
        f"ID: {market.id}",
        f"Slug: {market.slug}",
        f"Condition ID: {market.condition_id}",
        "",
        f"YES Price: {market.price_yes:.4f} ({market.price_yes*100:.1f}%)",
        f"NO Price: {market.price_no:.4f} ({market.price_no*100:.1f}%)",
        "",
        f"Volume: ${market.volume:,.2f}",
        f"Liquidity: ${market.liquidity:,.2f}",
        "",
        f"Token ID (YES): {market.token_id_yes}",
        f"Token ID (NO): {market.token_id_no}",
        "",
        f"Status: {'Closed' if market.closed else 'Active'}",
        f"URL: {market.url}",
    ]
    
    if market.description:
        lines.extend(["", f"Description: {market.description[:200]}..."])
    
    return "\n".join(lines)

