"""
Logging utilities for Polytrader.

Provides structured logging with rich console output and file logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from polytrader.config import get_config

# Global console instance
console = Console()

# Cache for loggers
_loggers: dict[str, logging.Logger] = {}


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    console_format: Optional[str] = None,
) -> None:
    """
    Set up logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        console_format: Console format ("simple" or "rich")
    """
    config = get_config()
    
    level = level or config.log_level
    log_file = log_file or config.log_file
    console_format = console_format or config.get("logging.console_format", "rich")
    
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger("polytrader")
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console_format == "rich":
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    if name not in _loggers:
        # Ensure logging is set up
        if not logging.getLogger("polytrader").handlers:
            setup_logging()
        
        # Create child logger
        if name.startswith("polytrader"):
            logger = logging.getLogger(name)
        else:
            logger = logging.getLogger(f"polytrader.{name}")
        
        _loggers[name] = logger
    
    return _loggers[name]


class TradeLogger:
    """
    Specialized logger for trade events.
    
    Logs trades in a structured format for easy analysis.
    """
    
    def __init__(self, name: str = "trades"):
        self.logger = get_logger(f"polytrader.{name}")
    
    def log_order_created(
        self,
        order_id: str,
        market_id: str,
        side: str,
        price: float,
        size: float,
    ) -> None:
        """Log order creation."""
        self.logger.info(
            f"ORDER CREATED | id={order_id} | market={market_id} | "
            f"{side} {size}@{price:.4f}"
        )
    
    def log_order_filled(
        self,
        order_id: str,
        fill_price: float,
        fill_size: float,
    ) -> None:
        """Log order fill."""
        self.logger.info(
            f"ORDER FILLED | id={order_id} | {fill_size}@{fill_price:.4f}"
        )
    
    def log_order_cancelled(self, order_id: str) -> None:
        """Log order cancellation."""
        self.logger.info(f"ORDER CANCELLED | id={order_id}")
    
    def log_position_opened(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
    ) -> None:
        """Log position opening."""
        self.logger.info(
            f"POSITION OPENED | market={market_id} | {side} {size}@{price:.4f}"
        )
    
    def log_position_closed(
        self,
        market_id: str,
        pnl: float,
    ) -> None:
        """Log position closing."""
        pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
        self.logger.info(f"POSITION CLOSED | market={market_id} | P&L={pnl_str}")
    
    def log_strategy_signal(
        self,
        strategy_name: str,
        market_id: str,
        signal: str,
        reason: str = "",
    ) -> None:
        """Log strategy signal."""
        msg = f"SIGNAL | strategy={strategy_name} | market={market_id} | {signal}"
        if reason:
            msg += f" | reason={reason}"
        self.logger.info(msg)


# Create default trade logger
trade_logger = TradeLogger()

