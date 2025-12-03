"""
BTC Volatility Term Structure Arbitrage Strategy.

This strategy trades across multiple Bitcoin up/down prediction markets
with different timeframes (15m, 1h, 4h, 24h) to exploit mispricings
in the implied probability term structure.

Key Features:
- Dynamic market discovery via Gamma API
- Auto-switches to new markets when current ones expire
- Detects term structure inversions and outliers
- Executes spread trades to capture arbitrage

Run with:
    polytrader run strategies/btc_term_structure_arb.py --paper
"""

import re
import time
from datetime import datetime, timedelta
from typing import Optional

from polytrader import Strategy, Market
from polytrader.core.client import PolymarketClient
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


class BTCTermStructureArb(Strategy):
    """
    Volatility term structure arbitrage strategy for BTC up/down markets.
    
    Core Logic:
    - Under random walk, P(Up) should be ~50% for all timeframes
    - Shorter timeframes should NOT have higher P(Up) than longer ones
    - When inversions occur, trade the spread
    """
    
    name = "btc_term_structure_arb"
    description = "Term structure arbitrage across BTC up/down timeframes"
    version = "1.0.0"
    
    # Initial market URLs (will be dynamically updated)
    markets = [
        "https://polymarket.com/event/btc-updown-15m-1764717300",
        "https://polymarket.com/event/bitcoin-up-or-down-december-2-6pm-et",
        "https://polymarket.com/event/btc-updown-4h-1764709200",
        "https://polymarket.com/event/bitcoin-up-or-down-on-december-3",
    ]
    
    # Timeframe definitions (in minutes)
    TIMEFRAMES = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "24h": 1440,
    }
    
    # Patterns to identify timeframe from market slug
    TIMEFRAME_PATTERNS = {
        "15m": [
            r"btc-updown-15m",
            r"bitcoin.*15.*min",
        ],
        "1h": [
            r"btc-updown-1h",
            r"bitcoin-up-or-down-[a-z]+-\d+-\d+-?\d*pm",  # e.g., december-2-6pm-et
            r"bitcoin-up-or-down-[a-z]+-\d+-\d+-?\d*am",
        ],
        "4h": [
            r"btc-updown-4h",
            r"bitcoin.*4.*hour",
        ],
        "24h": [
            r"bitcoin-up-or-down-on-",  # e.g., bitcoin-up-or-down-on-december-3
            r"btc-updown-24h",
            r"bitcoin.*daily",
        ],
    }
    
    # Trading parameters
    BASE_POSITION_SIZE = 50.0  # USDC per leg
    MAX_POSITION_PER_MARKET = 200.0  # Max exposure per market
    MIN_SPREAD_TO_TRADE = 0.03  # 3% minimum spread to enter
    EXIT_SPREAD_THRESHOLD = 0.01  # 1% spread to exit
    EXPIRY_BUFFER_MINUTES = 2  # Close positions this many minutes before expiry
    
    def __init__(self):
        super().__init__()
        
        # Mapping: timeframe -> current active market
        self._timeframe_markets: dict[str, Optional[Market]] = {
            "15m": None,
            "1h": None,
            "4h": None,
            "24h": None,
        }
        
        # Track term structure history
        self._term_structure_history: list[dict] = []
        
        # Active spread positions
        self._spread_positions: list[dict] = []
        
        # Last market discovery time
        self._last_discovery_time = 0
        self._discovery_interval = 60  # Re-discover markets every 60 seconds
        
        # API client for market discovery
        self._api_client = PolymarketClient()
        
        # Heartbeat / status tracking
        self._last_status_time = 0
        self._status_interval = 30  # Log status every 30 seconds
        self._price_updates_received = 0
        self._ws_messages_received = 0
    
    def on_start(self) -> None:
        """Initialize strategy and discover active markets."""
        self.log("Starting BTC Term Structure Arbitrage Strategy")
        self.log(f"Timeframes: {list(self.TIMEFRAMES.keys())}")
        self.log(f"Min spread to trade: {self.MIN_SPREAD_TO_TRADE:.1%}")
        
        # Initial market discovery
        self._discover_active_markets()
        
        # Log discovered markets
        for tf, market in self._timeframe_markets.items():
            if market:
                self.log(f"  {tf}: {market.question[:50]}... (YES: {market.price_yes:.2%})")
            else:
                self.log(f"  {tf}: No active market found", level="warning")
    
    def on_stop(self) -> None:
        """Clean up and report final stats."""
        self.log("Stopping strategy")
        self.log(f"Total trades: {self._stats['total_trades']}")
        self.log(f"Active spread positions: {len(self._spread_positions)}")
        
        # Close any remaining positions
        if self._spread_positions:
            self.log("Closing remaining spread positions...")
            for spread in self._spread_positions:
                self._close_spread_position(spread)
    
    def on_price_update(self, market: Market, price: float) -> None:
        """
        Main trading logic - called on every price update.
        
        1. Update term structure
        2. Check for market expiry / discover new markets
        3. Detect arbitrage opportunities
        4. Execute or manage spread trades
        """
        # Track price updates received
        self._price_updates_received += 1
        
        # Periodically re-discover markets
        current_time = time.time()
        
        # Log periodic status update (heartbeat)
        if current_time - self._last_status_time > self._status_interval:
            self._log_status()
            self._last_status_time = current_time
        
        if current_time - self._last_discovery_time > self._discovery_interval:
            self._discover_active_markets()
            self._last_discovery_time = current_time
        
        # Update our market mapping
        timeframe = self._get_market_timeframe(market)
        if timeframe:
            self._timeframe_markets[timeframe] = market
        
        # Calculate current term structure
        term_structure = self._calculate_term_structure()
        
        if not term_structure:
            return
        
        # Store for analysis
        self._term_structure_history.append({
            "timestamp": datetime.now(),
            "structure": term_structure.copy(),
        })
        
        # Keep only last 100 data points
        if len(self._term_structure_history) > 100:
            self._term_structure_history = self._term_structure_history[-100:]
        
        # Log term structure periodically
        if len(self._term_structure_history) % 10 == 1:
            self._log_term_structure(term_structure)
        
        # Check for arbitrage opportunities
        opportunities = self._find_arbitrage_opportunities(term_structure)
        
        for opp in opportunities:
            self._execute_arbitrage(opp)
        
        # Manage existing positions
        self._manage_spread_positions(term_structure)
    
    def _discover_active_markets(self) -> None:
        """
        Discover active BTC up/down markets.
        
        Strategy:
        1. First, try to fetch markets from the initial URLs/slugs
        2. Then search the Gamma API for any additional BTC up/down markets
        3. Classify each by timeframe
        """
        self.log("Discovering active BTC up/down markets...")
        
        found_markets = []
        
        # Step 1: Fetch markets from initial slugs
        initial_slugs = [
            "btc-updown-15m-1764717300",
            "bitcoin-up-or-down-december-2-6pm-et",
            "btc-updown-4h-1764709200",
            "bitcoin-up-or-down-on-december-3",
        ]
        
        for slug in initial_slugs:
            try:
                market = self._api_client.get_market_by_slug(slug)
                if market and not market.closed:
                    found_markets.append(market)
                    self.log(f"  Found market: {slug}")
            except Exception as e:
                self.log(f"  Could not fetch {slug}: {e}", level="debug")
        
        # Step 2: Also search Gamma API for any BTC up/down markets
        try:
            all_markets = self._api_client.get_markets(closed=False, limit=500)
            
            for market in all_markets:
                question = market.question.lower()
                
                # Check if it's a BTC up/down market
                if ("bitcoin" in question or "btc" in question) and \
                   ("up" in question and "down" in question):
                    # Avoid duplicates
                    if not any(m.id == market.id for m in found_markets):
                        found_markets.append(market)
        except Exception as e:
            self.log(f"Error searching Gamma API: {e}", level="warning")
        
        self.log(f"Found {len(found_markets)} BTC up/down markets total")
        
        # Step 3: Classify each market by timeframe
        for market in found_markets:
            timeframe = self._classify_timeframe(market.slug)
            if timeframe:
                # Update if this is a newer/more active market
                current = self._timeframe_markets.get(timeframe)
                if current is None or market.volume > current.volume:
                    self._timeframe_markets[timeframe] = market
                    
                    # Also add to strategy's tracked markets
                    if market.id not in self._markets:
                        self._markets[market.id] = market
            else:
                self.log(f"  Could not classify timeframe for: {market.slug}", level="debug")
    
    def _classify_timeframe(self, slug: str) -> Optional[str]:
        """Classify a market slug into a timeframe category."""
        slug_lower = slug.lower()
        
        for timeframe, patterns in self.TIMEFRAME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, slug_lower):
                    return timeframe
        
        return None
    
    def _get_market_timeframe(self, market: Market) -> Optional[str]:
        """Get the timeframe for a given market."""
        return self._classify_timeframe(market.slug)
    
    def _calculate_term_structure(self) -> dict[str, float]:
        """
        Calculate the current term structure (YES prices across timeframes).
        
        Returns dict mapping timeframe to YES price.
        """
        structure = {}
        
        for timeframe in ["15m", "1h", "4h", "24h"]:
            market = self._timeframe_markets.get(timeframe)
            if market and market.price_yes > 0:
                structure[timeframe] = market.price_yes
        
        return structure
    
    def _log_term_structure(self, structure: dict[str, float]) -> None:
        """Log the current term structure."""
        parts = []
        for tf in ["15m", "1h", "4h", "24h"]:
            if tf in structure:
                parts.append(f"{tf}={structure[tf]:.1%}")
            else:
                parts.append(f"{tf}=N/A")
        
        self.log(f"Term Structure: {' | '.join(parts)}")
    
    def _log_status(self) -> None:
        """Log periodic status update (heartbeat)."""
        structure = self._calculate_term_structure()
        active_markets = sum(1 for m in self._timeframe_markets.values() if m is not None)
        
        # Build term structure string
        ts_parts = []
        for tf in ["15m", "1h", "4h", "24h"]:
            if tf in structure:
                ts_parts.append(f"{tf}:{structure[tf]:.0%}")
        ts_str = " | ".join(ts_parts) if ts_parts else "No data"
        
        self.log(
            f"💓 HEARTBEAT | Updates: {self._price_updates_received} | "
            f"Markets: {active_markets}/4 | Positions: {len(self._spread_positions)} | "
            f"[{ts_str}]"
        )
        
        # Reset counter
        self._price_updates_received = 0
    
    def on_heartbeat(self) -> None:
        """Called periodically by the runner to show strategy is alive."""
        structure = self._calculate_term_structure()
        active_markets = sum(1 for m in self._timeframe_markets.values() if m is not None)
        
        # Build term structure string
        ts_parts = []
        for tf in ["15m", "1h", "4h", "24h"]:
            if tf in structure:
                ts_parts.append(f"{tf}:{structure[tf]:.0%}")
        ts_str = " | ".join(ts_parts) if ts_parts else "No data"
        
        self.log(
            f"💓 ALIVE | Price updates: {self._price_updates_received} | "
            f"WS msgs: {self._ws_messages_received} | "
            f"Markets: {active_markets}/4 | Positions: {len(self._spread_positions)} | "
            f"[{ts_str}]"
        )
    
    def _find_arbitrage_opportunities(self, structure: dict[str, float]) -> list[dict]:
        """
        Detect arbitrage opportunities in the term structure.
        
        Types of opportunities:
        1. Inversion: Shorter timeframe has higher YES price than longer
        2. Outlier: One timeframe significantly deviates from neighbors
        """
        opportunities = []
        
        if len(structure) < 2:
            return opportunities
        
        timeframes_ordered = ["15m", "1h", "4h", "24h"]
        available = [tf for tf in timeframes_ordered if tf in structure]
        
        # Check for inversions between adjacent timeframes
        for i in range(len(available) - 1):
            short_tf = available[i]
            long_tf = available[i + 1]
            
            short_price = structure[short_tf]
            long_price = structure[long_tf]
            
            spread = short_price - long_price
            
            # Inversion: short timeframe YES > long timeframe YES
            if spread > self.MIN_SPREAD_TO_TRADE:
                opportunities.append({
                    "type": "inversion",
                    "long_tf": long_tf,  # Buy this (underpriced)
                    "short_tf": short_tf,  # Sell this (overpriced)
                    "spread": spread,
                    "confidence": min(spread / 0.10, 1.0),  # Scale by spread size
                })
                
                self.log(
                    f"INVERSION DETECTED: {short_tf} ({short_price:.1%}) > "
                    f"{long_tf} ({long_price:.1%}), spread={spread:.1%}"
                )
        
        # Check for outliers (one timeframe significantly different from mean)
        if len(available) >= 3:
            mean_price = sum(structure[tf] for tf in available) / len(available)
            
            for tf in available:
                deviation = abs(structure[tf] - mean_price)
                
                if deviation > self.MIN_SPREAD_TO_TRADE * 1.5:
                    # This timeframe is an outlier
                    is_overpriced = structure[tf] > mean_price
                    
                    opportunities.append({
                        "type": "outlier",
                        "outlier_tf": tf,
                        "direction": "sell" if is_overpriced else "buy",
                        "deviation": deviation,
                        "mean_price": mean_price,
                        "confidence": min(deviation / 0.15, 1.0),
                    })
                    
                    self.log(
                        f"OUTLIER DETECTED: {tf} ({structure[tf]:.1%}) "
                        f"{'above' if is_overpriced else 'below'} mean ({mean_price:.1%}), "
                        f"deviation={deviation:.1%}"
                    )
        
        return opportunities
    
    def _execute_arbitrage(self, opportunity: dict) -> None:
        """Execute an arbitrage trade based on the opportunity."""
        # Check if we already have a position for this opportunity
        for existing in self._spread_positions:
            if self._is_same_opportunity(existing, opportunity):
                return  # Already have this position
        
        # Check exposure limits
        current_exposure = self._calculate_total_exposure()
        if current_exposure >= self.MAX_POSITION_PER_MARKET * 4:
            self.log("Max exposure reached, skipping trade", level="warning")
            return
        
        # Calculate position size based on confidence
        size = self.BASE_POSITION_SIZE * opportunity.get("confidence", 1.0)
        
        if opportunity["type"] == "inversion":
            self._execute_inversion_trade(opportunity, size)
        elif opportunity["type"] == "outlier":
            self._execute_outlier_trade(opportunity, size)
    
    def _execute_inversion_trade(self, opp: dict, size: float) -> None:
        """Execute a spread trade for an inversion opportunity."""
        long_market = self._timeframe_markets.get(opp["long_tf"])
        short_market = self._timeframe_markets.get(opp["short_tf"])
        
        if not long_market or not short_market:
            return
        
        self.signal(
            long_market,
            "SPREAD_ENTRY",
            f"Buy {opp['long_tf']}, Sell {opp['short_tf']}, spread={opp['spread']:.1%}"
        )
        
        # Buy the underpriced (longer timeframe)
        buy_order = self.buy(long_market, size=size, outcome="YES")
        
        # Sell the overpriced (shorter timeframe) - buy NO instead
        sell_order = self.buy(short_market, size=size, outcome="NO")
        
        if buy_order and sell_order:
            self._spread_positions.append({
                "type": "inversion",
                "long_tf": opp["long_tf"],
                "short_tf": opp["short_tf"],
                "entry_spread": opp["spread"],
                "size": size,
                "entry_time": datetime.now(),
                "long_market_id": long_market.id,
                "short_market_id": short_market.id,
            })
            
            self.log(
                f"SPREAD ENTERED: Long {opp['long_tf']} / Short {opp['short_tf']}, "
                f"size=${size:.2f}, spread={opp['spread']:.1%}"
            )
    
    def _execute_outlier_trade(self, opp: dict, size: float) -> None:
        """Execute a trade for an outlier opportunity."""
        market = self._timeframe_markets.get(opp["outlier_tf"])
        
        if not market:
            return
        
        if opp["direction"] == "sell":
            # Outlier is overpriced - buy NO
            self.signal(market, "OUTLIER_SELL", f"Sell {opp['outlier_tf']} (overpriced)")
            order = self.buy(market, size=size, outcome="NO")
        else:
            # Outlier is underpriced - buy YES
            self.signal(market, "OUTLIER_BUY", f"Buy {opp['outlier_tf']} (underpriced)")
            order = self.buy(market, size=size, outcome="YES")
        
        if order:
            self._spread_positions.append({
                "type": "outlier",
                "outlier_tf": opp["outlier_tf"],
                "direction": opp["direction"],
                "entry_deviation": opp["deviation"],
                "size": size,
                "entry_time": datetime.now(),
                "market_id": market.id,
            })
            
            self.log(
                f"OUTLIER TRADE: {opp['direction'].upper()} {opp['outlier_tf']}, "
                f"size=${size:.2f}, deviation={opp['deviation']:.1%}"
            )
    
    def _manage_spread_positions(self, structure: dict[str, float]) -> None:
        """Manage existing spread positions - check for exit conditions."""
        positions_to_close = []
        
        for i, pos in enumerate(self._spread_positions):
            should_close = False
            reason = ""
            
            if pos["type"] == "inversion":
                # Check if spread has narrowed
                long_tf = pos["long_tf"]
                short_tf = pos["short_tf"]
                
                if long_tf in structure and short_tf in structure:
                    current_spread = structure[short_tf] - structure[long_tf]
                    
                    if current_spread <= self.EXIT_SPREAD_THRESHOLD:
                        should_close = True
                        reason = f"Spread narrowed to {current_spread:.1%}"
                    elif current_spread < 0:
                        should_close = True
                        reason = f"Spread inverted (profit): {current_spread:.1%}"
            
            elif pos["type"] == "outlier":
                # Check if outlier has reverted to mean
                tf = pos["outlier_tf"]
                if tf in structure:
                    mean_price = sum(structure.values()) / len(structure)
                    current_deviation = abs(structure[tf] - mean_price)
                    
                    if current_deviation <= self.EXIT_SPREAD_THRESHOLD:
                        should_close = True
                        reason = f"Outlier reverted, deviation={current_deviation:.1%}"
            
            # Check time-based exit (position too old)
            age = datetime.now() - pos["entry_time"]
            if age > timedelta(hours=1):
                should_close = True
                reason = f"Position aged out ({age})"
            
            if should_close:
                positions_to_close.append((i, pos, reason))
        
        # Close positions (reverse order to maintain indices)
        for i, pos, reason in reversed(positions_to_close):
            self._close_spread_position(pos, reason)
            self._spread_positions.pop(i)
    
    def _close_spread_position(self, pos: dict, reason: str = "") -> None:
        """Close a spread position."""
        self.log(f"CLOSING POSITION: {pos['type']} - {reason}")
        
        if pos["type"] == "inversion":
            long_market = self._timeframe_markets.get(pos["long_tf"])
            short_market = self._timeframe_markets.get(pos["short_tf"])
            
            if long_market:
                self.sell(long_market, outcome="YES")
            if short_market:
                self.sell(short_market, outcome="NO")
        
        elif pos["type"] == "outlier":
            market = self._timeframe_markets.get(pos["outlier_tf"])
            if market:
                outcome = "NO" if pos["direction"] == "sell" else "YES"
                self.sell(market, outcome=outcome)
    
    def _is_same_opportunity(self, existing: dict, new: dict) -> bool:
        """Check if two opportunities are essentially the same."""
        if existing["type"] != new["type"]:
            return False
        
        if existing["type"] == "inversion":
            return (existing["long_tf"] == new["long_tf"] and 
                    existing["short_tf"] == new["short_tf"])
        
        elif existing["type"] == "outlier":
            return (existing["outlier_tf"] == new["outlier_tf"] and
                    existing["direction"] == new["direction"])
        
        return False
    
    def _calculate_total_exposure(self) -> float:
        """Calculate total current exposure across all positions."""
        return sum(pos.get("size", 0) for pos in self._spread_positions)
    
    def on_fill(self, order, trade) -> None:
        """Handle order fills."""
        self.log(f"Order filled: {trade.side.value} {trade.size}@{trade.price:.4f}")
        self._stats["total_trades"] += 1
    
    def on_error(self, error: Exception) -> None:
        """Handle errors."""
        self.log(f"Error: {error}", level="error")
    
    def on_orderbook_update(self, market: Market, orderbook: dict) -> None:
        """Handle orderbook updates from WebSocket."""
        self._ws_messages_received += 1
        # Log every 50th message to show activity without spam
        if self._ws_messages_received % 50 == 1:
            self.log(f"📊 WS Activity | Messages: {self._ws_messages_received} | Market: {market.slug[:30]}...")
    
    def on_market_trade(self, market: Market, data: dict) -> None:
        """Handle trade events from WebSocket (other users' trades)."""
        self._ws_messages_received += 1
        price = data.get("price", "?")
        size = data.get("size", "?")
        side = data.get("side", "?")
        # Log trades to show market activity
        if self._ws_messages_received % 20 == 1:
            self.log(f"🔄 Market Trade | {market.slug[:25]}... | {side} {size}@{price}")


# Default export
DefaultStrategy = BTCTermStructureArb

