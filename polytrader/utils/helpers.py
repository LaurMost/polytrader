"""
Helper utilities for Polytrader.
"""

from datetime import datetime, timezone
from typing import Optional, Union


def format_price(price: float, decimals: int = 4) -> str:
    """
    Format a price for display.
    
    Args:
        price: Price value (0-1 for prediction markets)
        decimals: Number of decimal places
        
    Returns:
        Formatted price string
    """
    return f"{price:.{decimals}f}"


def format_amount(amount: float, decimals: int = 2) -> str:
    """
    Format an amount (USDC) for display.
    
    Args:
        amount: Amount value
        decimals: Number of decimal places
        
    Returns:
        Formatted amount string with $ prefix
    """
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.{decimals}f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.{decimals}f}K"
    else:
        return f"${amount:.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format a value as percentage.
    
    Args:
        value: Value (0-1)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_pnl(pnl: float, decimals: int = 2) -> str:
    """
    Format P&L for display with +/- sign.
    
    Args:
        pnl: Profit/loss value
        decimals: Number of decimal places
        
    Returns:
        Formatted P&L string
    """
    sign = "+" if pnl >= 0 else ""
    return f"{sign}${pnl:.{decimals}f}"


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """
    Convert Unix timestamp to datetime.
    
    Args:
        timestamp: Unix timestamp (seconds)
        
    Returns:
        datetime object in UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: datetime object
        
    Returns:
        Unix timestamp (seconds)
    """
    return int(dt.timestamp())


def now_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(datetime.now(timezone.utc).timestamp())


def format_duration(seconds: float) -> str:
    """
    Format a duration in human-readable form.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp a value between min and max.
    
    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value
        
    Returns:
        Clamped value
    """
    return max(min_value, min(value, max_value))


def round_price(price: float, tick_size: float = 0.001) -> float:
    """
    Round a price to the nearest tick size.
    
    Args:
        price: Price to round
        tick_size: Minimum price increment
        
    Returns:
        Rounded price
    """
    return round(price / tick_size) * tick_size


def calculate_position_size(
    balance: float,
    risk_percent: float,
    entry_price: float,
    stop_price: float,
) -> float:
    """
    Calculate position size based on risk management.
    
    Args:
        balance: Account balance
        risk_percent: Percentage of balance to risk (0-1)
        entry_price: Entry price
        stop_price: Stop loss price
        
    Returns:
        Position size
    """
    risk_amount = balance * risk_percent
    price_diff = abs(entry_price - stop_price)
    
    if price_diff == 0:
        return 0
    
    return risk_amount / price_diff


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    size: float,
    is_long: bool = True,
) -> float:
    """
    Calculate P&L for a trade.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        size: Position size
        is_long: True if long position
        
    Returns:
        Profit/loss amount
    """
    if is_long:
        return (exit_price - entry_price) * size
    else:
        return (entry_price - exit_price) * size


def calculate_return(
    entry_price: float,
    exit_price: float,
    is_long: bool = True,
) -> float:
    """
    Calculate percentage return for a trade.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        is_long: True if long position
        
    Returns:
        Percentage return (0-1)
    """
    if entry_price == 0:
        return 0
    
    if is_long:
        return (exit_price - entry_price) / entry_price
    else:
        return (entry_price - exit_price) / entry_price

