"""
Polymarket API client wrapper.

Wraps py-clob-client with additional features:
- Paper trading mode
- Rate limiting
- Retry logic
- Simplified interface
"""

import json
import time
from typing import Any, Optional

import requests

from polytrader.config import get_config
from polytrader.data.models import Market, Order, OrderSide, OrderStatus, OrderType
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


class PolymarketClient:
    """
    Wrapper around Polymarket's py-clob-client with paper trading support.
    
    Usage:
        client = PolymarketClient()
        
        # Get market info
        market = client.get_market("0x...")
        
        # Place order
        order = client.create_order(
            token_id="...",
            side=OrderSide.BUY,
            price=0.5,
            size=100
        )
    """

    # API endpoints
    GAMMA_API = "https://gamma-api.polymarket.com"
    CLOB_API = "https://clob.polymarket.com"

    def __init__(
        self,
        private_key: Optional[str] = None,
        host: Optional[str] = None,
        chain_id: Optional[int] = None,
    ):
        """Initialize the client."""
        self.config = get_config()
        
        self._private_key = private_key or self.config.private_key
        self._host = host or self.config.host
        self._chain_id = chain_id or self.config.chain_id
        
        self._clob_client = None
        self._session = requests.Session()
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
        
        # Initialize CLOB client for live trading
        if self.config.is_live and self._private_key:
            self._init_clob_client()

    def _init_clob_client(self) -> None:
        """Initialize the py-clob-client for live trading."""
        try:
            from py_clob_client.client import ClobClient
            
            self._clob_client = ClobClient(
                host=self._host,
                key=self._private_key,
                chain_id=self._chain_id,
            )
            logger.info("CLOB client initialized for live trading")
        except ImportError:
            logger.warning("py-clob-client not installed. Live trading disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize CLOB client: {e}")

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        retries: int = 3,
    ) -> Optional[dict]:
        """Make an HTTP request with retry logic."""
        self._rate_limit()
        
        for attempt in range(retries):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=30,
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif e.response.status_code >= 500:
                    # Server error - retry
                    logger.warning(f"Server error {e.response.status_code}. Retrying...")
                    time.sleep(1)
                else:
                    logger.error(f"HTTP error: {e}")
                    return None
            except Exception as e:
                logger.error(f"Request failed: {e}")
                if attempt < retries - 1:
                    time.sleep(1)
        
        return None

    # ==================== Market Data ====================

    def get_markets(
        self,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Market]:
        """Fetch list of markets from Gamma API."""
        params = {
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
            "order": "volume24hr",
            "ascending": "false",
        }
        
        data = self._request("GET", f"{self.GAMMA_API}/markets", params=params)
        if not data:
            return []
        
        markets = []
        for item in data:
            market = self._parse_market(item)
            if market:
                markets.append(market)
        
        return markets

    def get_market_by_id(self, market_id: str) -> Optional[Market]:
        """Fetch a single market by ID."""
        data = self._request("GET", f"{self.GAMMA_API}/markets/{market_id}")
        if data:
            return self._parse_market(data)
        return None

    def get_market_by_slug(self, slug: str) -> Optional[Market]:
        """Fetch a market by its URL slug."""
        data = self._request("GET", f"{self.GAMMA_API}/markets/slug/{slug}")
        if data:
            return self._parse_market(data)
        return None

    def get_event(self, event_slug: str) -> Optional[dict]:
        """Fetch an event with all its markets."""
        data = self._request("GET", f"{self.GAMMA_API}/events/slug/{event_slug}")
        return data

    def _parse_market(self, data: dict) -> Optional[Market]:
        """Parse market data from API response."""
        try:
            # Parse token IDs
            token_ids = data.get("clobTokenIds", "[]")
            if isinstance(token_ids, str):
                token_ids = json.loads(token_ids)
            
            token_id_yes = token_ids[0] if len(token_ids) > 0 else ""
            token_id_no = token_ids[1] if len(token_ids) > 1 else ""
            
            # Parse prices
            outcome_prices = data.get("outcomePrices", "[]")
            if isinstance(outcome_prices, str):
                outcome_prices = json.loads(outcome_prices)
            
            price_yes = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.0
            price_no = float(outcome_prices[1]) if len(outcome_prices) > 1 else 0.0
            
            return Market(
                id=str(data.get("id", "")),
                condition_id=data.get("conditionId", ""),
                question=data.get("question", ""),
                slug=data.get("slug", ""),
                token_id_yes=token_id_yes,
                token_id_no=token_id_no,
                price_yes=price_yes,
                price_no=price_no,
                volume=float(data.get("volume", 0)),
                liquidity=float(data.get("liquidity", 0)),
                description=data.get("description", ""),
                category=data.get("category", ""),
                active=data.get("active", True),
                closed=data.get("closed", False),
            )
        except Exception as e:
            logger.error(f"Failed to parse market: {e}")
            return None

    def get_price_history(
        self,
        token_id: str,
        interval: str = "max",
        fidelity: int = 1440,
    ) -> list[dict]:
        """Fetch price history for a token."""
        params = {
            "market": token_id,
            "interval": interval,
            "fidelity": fidelity,
        }
        
        data = self._request("GET", f"{self.CLOB_API}/prices-history", params=params)
        if data and "history" in data:
            return data["history"]
        return []

    def get_orderbook(self, token_id: str) -> Optional[dict]:
        """Fetch orderbook for a token."""
        params = {"token_id": token_id}
        return self._request("GET", f"{self.CLOB_API}/book", params=params)

    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token."""
        params = {"token_id": token_id}
        data = self._request("GET", f"{self.CLOB_API}/midpoint", params=params)
        if data and "mid" in data:
            return float(data["mid"])
        return None

    def get_spread(self, token_id: str) -> Optional[dict]:
        """Get bid-ask spread for a token."""
        params = {"token_id": token_id}
        return self._request("GET", f"{self.CLOB_API}/spread", params=params)

    # ==================== Trading (Live Mode) ====================

    def create_order(
        self,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
    ) -> Optional[Order]:
        """
        Create a new order.
        
        In paper mode, returns a simulated order.
        In live mode, places a real order via py-clob-client.
        """
        if self.config.is_paper:
            return self._create_paper_order(token_id, side, price, size, order_type)
        
        if not self._clob_client:
            logger.error("CLOB client not initialized. Cannot place live orders.")
            return None
        
        try:
            # Use py-clob-client to create order
            order_args = {
                "token_id": token_id,
                "price": price,
                "size": size,
                "side": side.value,
            }
            
            result = self._clob_client.create_order(order_args)
            
            if result and "orderID" in result:
                return Order(
                    id=result["orderID"],
                    market_id="",  # Will be filled by executor
                    token_id=token_id,
                    side=side,
                    order_type=order_type,
                    status=OrderStatus.OPEN,
                    price=price,
                    size=size,
                    is_paper=False,
                )
            
            logger.error(f"Failed to create order: {result}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def _create_paper_order(
        self,
        token_id: str,
        side: OrderSide,
        price: float,
        size: float,
        order_type: OrderType,
    ) -> Order:
        """Create a simulated paper order."""
        import uuid
        
        return Order(
            id=f"paper_{uuid.uuid4().hex[:12]}",
            market_id="",
            token_id=token_id,
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            price=price,
            size=size,
            is_paper=True,
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        if self.config.is_paper:
            logger.info(f"Paper mode: Cancelled order {order_id}")
            return True
        
        if not self._clob_client:
            logger.error("CLOB client not initialized")
            return False
        
        try:
            result = self._clob_client.cancel(order_id)
            return result.get("canceled", False)
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    def get_orders(self, market_id: Optional[str] = None) -> list[dict]:
        """Get open orders."""
        if self.config.is_paper:
            return []  # Paper orders tracked separately
        
        if not self._clob_client:
            return []
        
        try:
            params = {}
            if market_id:
                params["market"] = market_id
            return self._clob_client.get_orders(params) or []
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def get_trades(self, market_id: Optional[str] = None) -> list[dict]:
        """Get trade history."""
        if not self._clob_client:
            return []
        
        try:
            params = {}
            if market_id:
                params["market"] = market_id
            return self._clob_client.get_trades(params) or []
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []

    # ==================== Account ====================

    def get_balance(self) -> float:
        """Get USDC balance."""
        if self.config.is_paper:
            return self.config.get("paper.starting_balance", 10000.0)
        
        if not self._clob_client:
            return 0.0
        
        try:
            # This would need the actual balance endpoint
            # For now, return 0 as placeholder
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0

    def __repr__(self) -> str:
        mode = "paper" if self.config.is_paper else "live"
        return f"PolymarketClient(mode={mode}, host={self._host})"

